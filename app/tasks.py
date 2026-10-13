import threading
import time
import uuid

from .stats import TaskStats

PENDING = "pending"
RUNNING = "running"
DONE = "done"
STOPPED = "stopped"
ERROR = "error"

TERMINAL = {DONE, STOPPED, ERROR}

STATUS_TEXT = {
    PENDING: "等待中",
    RUNNING: "检测中",
    DONE: "已完成",
    STOPPED: "已停止",
    ERROR: "处理失败",
}


class Task:
    def __init__(self, kind: str):
        self.id = uuid.uuid4().hex
        self.kind = kind
        self.status = PENDING
        self.error = None
        self.created_at = time.time()
        self.stop_event = threading.Event()
        self.stats = TaskStats()
        self.source_name = None
        self.latest_jpeg = None
        self.frame_lock = threading.Lock()

    def set_frame(self, jpeg_bytes):
        with self.frame_lock:
            self.latest_jpeg = jpeg_bytes

    def request_stop(self):
        self.stop_event.set()

    def status_payload(self):
        return {
            "task_id": self.id,
            "status": self.status,
            "status_text": STATUS_TEXT.get(self.status, self.status),
            "error": self.error,
            "source_name": self.source_name,
            "stats": self.stats.snapshot(),
        }


class TaskRegistry:
    def __init__(self):
        self._tasks = {}
        self._lock = threading.Lock()

    def create(self, kind: str) -> Task:
        task = Task(kind)
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str):
        with self._lock:
            return self._tasks.get(task_id)

    def active_of(self, kind: str):
        with self._lock:
            for task in self._tasks.values():
                if task.kind == kind and task.status not in TERMINAL:
                    return task
        return None

    def remove(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)
