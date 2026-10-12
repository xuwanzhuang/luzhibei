# 火点/烟雾目标检测 Web 应用 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 基于已训练 YOLO 权重，交付一个本地可运行的 Web 应用，支持图片与视频两种检测模式，形成「媒体输入 → 内容校验 → 模型推理 → 结果展示 → 统计告警」闭环。

**架构：** FastAPI 后端负责文件校验、模型推理、任务状态机与权威统计；原生 HTML/JS 前端负责上传、结果展示与状态轮询；视频采用后台线程逐帧推理 + MJPEG 流式输出，支持中途停止。

**技术栈：** Python 3.12（conda 环境 `aigc`）、FastAPI、Uvicorn、ultralytics(YOLO)、OpenCV、pytest、原生 HTML/CSS/JS。

**运行时解释器：** `D:\miniconda\envs\aigc\python.exe`

**语言约定：** 所有面向用户的提示、页面文案、README 使用中文。

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `app/__init__.py` | 包标记 |
| `app/config.py` | 常量：路径、扩展名/MIME 白名单、大小上限、置信度阈值、类别映射、风险等级 |
| `app/validators.py` | 文件校验与解码；`ValidationError` |
| `app/stats.py` | 分类计数、风险映射、任务级累计统计 |
| `app/tasks.py` | 任务状态机、内存任务表、停止信号 |
| `app/detector.py` | YOLO 单例加载与推理封装；`ModelNotLoadedError` |
| `app/routers/image.py` | `POST /api/detect/image` |
| `app/routers/video.py` | 视频上传/流/状态/停止四个接口 |
| `app/main.py` | 应用装配、异常处理器、静态托管 |
| `static/index.html` `static/style.css` `static/app.js` | 前端单页 |
| `tests/test_validators.py` `tests/test_stats.py` `tests/test_tasks.py` | 单元测试 |
| `requirements.txt` `README.md` | 交付配置与说明 |

---

## 任务 0：项目骨架与依赖

**文件：**
- 创建：`app/__init__.py`、`app/routers/__init__.py`、`tests/__init__.py`、`models/.gitkeep`
- 创建：`requirements.txt`

- [ ] **步骤 1：创建包目录占位文件**

`app/__init__.py`、`app/routers/__init__.py`、`tests/__init__.py` 内容留空；`models/.gitkeep` 留空。

- [ ] **步骤 2：编写 requirements.txt**

```text
fastapi==0.143.0
uvicorn==0.54.0
ultralytics==8.4.175
opencv-python==5.0.0.93
numpy==2.5.4
pillow==12.3.0
python-multipart>=0.0.9
pytest>=8.0.0
```

- [ ] **步骤 3：确认 aigc 环境已具备依赖（含 pytest 与 python-multipart）**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pip install python-multipart pytest`
预期：已安装或提示 already satisfied。

- [ ] **步骤 4：下载占位模型（权重到位前的临时方案）**

运行：`& "D:\miniconda\envs\aigc\python.exe" -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"`
预期：在 `models/` 之外生成 `yolov8n.pt`；将其移动到 `models/yolov8n.pt`。
说明：真实权重 `权重.pt` 就位后，仅修改 `config.MODEL_PATH` 即可，无需改其它代码。

- [ ] **步骤 5：Commit**

```bash
git add app tests models/.gitkeep requirements.txt
git commit -m "chore: 初始化工程骨架与依赖配置"
```

---

## 任务 1：配置常量 `app/config.py`

**文件：**
- 创建：`app/config.py`

- [ ] **步骤 1：编写实现**

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"

MODEL_PATH = MODELS_DIR / "yolov8n.pt"

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mp4", ".avi", ".mov"}
IMAGE_MIME = {"image/jpeg", "image/png"}
VIDEO_MIME = {"video/mp4", "video/x-msvideo", "video/quicktime"}
OCTET_STREAM = {"application/octet-stream", ""}

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024

CONF_THRESHOLD = 0.25

FIRE_LABELS = {"fire", "flame", "火点", "火焰"}
SMOKE_LABELS = {"smoke", "烟雾"}

RISK_NORMAL = "normal"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

RISK_TEXT = {
    RISK_NORMAL: "未检测到火点或烟雾",
    RISK_MEDIUM: "检测到烟雾，请关注现场情况",
    RISK_HIGH: "检测到火点，请立即人工复核",
}
```

- [ ] **步骤 2：Commit**

```bash
git add app/config.py
git commit -m "feat: 新增配置常量模块"
```

---

## 任务 2：文件校验 `app/validators.py`（TDD）

**文件：**
- 创建：`app/validators.py`
- 测试：`tests/test_validators.py`

- [ ] **步骤 1：编写失败的测试**

```python
import io
import numpy as np
import cv2
import pytest
from app import validators
from app.validators import ValidationError


def _png_bytes():
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_valid_image_passes():
    validators.validate_image("a.png", "image/png", _png_bytes())


def test_bad_extension_rejected():
    with pytest.raises(ValidationError) as e:
        validators.validate_image("a.txt", "text/plain", b"x")
    assert "类型" in e.value.message


def test_oversize_image_rejected():
    with pytest.raises(ValidationError):
        validators.validate_image("a.png", "image/png", b"0" * (11 * 1024 * 1024))


def test_undecodable_image_rejected():
    with pytest.raises(ValidationError) as e:
        validators.validate_image("a.png", "image/png", b"not-an-image")
    assert "读取" in e.value.message or "损坏" in e.value.message


def test_decode_image_returns_array():
    frame = validators.decode_image(_png_bytes())
    assert frame.shape[0] == 32 and frame.shape[1] == 32
```

- [ ] **步骤 2：运行测试验证失败**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_validators.py -v`
预期：FAIL，`ModuleNotFoundError` 或 `AttributeError`（validators 尚未实现）。

- [ ] **步骤 3：编写实现**

```python
import os
import tempfile

import cv2
import numpy as np

from . import config


class ValidationError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _ext(filename):
    return os.path.splitext(filename or "")[1].lower()


def _check_ext(filename, allowed, kind):
    if _ext(filename) not in allowed:
        raise ValidationError(400, f"不支持的文件类型，{kind}仅支持：{', '.join(sorted(allowed))}")


def _check_mime(content_type, allowed):
    ct = (content_type or "").lower()
    if ct in config.OCTET_STREAM:
        return
    if ct not in allowed:
        raise ValidationError(400, f"不支持的文件类型：{ct}")


def _check_size(size, maximum, kind):
    if size > maximum:
        raise ValidationError(413, f"{kind}文件过大，上限 {maximum // (1024 * 1024)}MB")


def validate_image(filename, content_type, data):
    _check_ext(filename, config.IMAGE_EXTS, "图片")
    _check_mime(content_type, config.IMAGE_MIME)
    _check_size(len(data), config.MAX_IMAGE_BYTES, "图片")
    _check_decodable_image(data)


def _check_decodable_image(data):
    if not data:
        raise ValidationError(400, "文件内容为空，无法读取")
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValidationError(400, "文件已损坏或无法读取，请更换文件")


def decode_image(data):
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValidationError(400, "文件已损坏或无法读取，请更换文件")
    return frame


def validate_video(filename, content_type, data):
    _check_ext(filename, config.VIDEO_EXTS, "视频")
    _check_mime(content_type, config.VIDEO_MIME)
    _check_size(len(data), config.MAX_VIDEO_BYTES, "视频")
    if not data:
        raise ValidationError(400, "文件内容为空，无法读取")
    tmp = _write_temp(data, _ext(filename))
    try:
        cap = cv2.VideoCapture(tmp)
        if not cap.isOpened():
            raise ValidationError(400, "视频文件已损坏或无法读取，请更换文件")
        ok, _ = cap.read()
        cap.release()
        if not ok:
            raise ValidationError(400, "视频没有可读取的画面，请更换文件")
    finally:
        _safe_remove(tmp)


def save_video_temp(data, filename):
    return _write_temp(data, _ext(filename))


def _write_temp(data, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass
```

- [ ] **步骤 4：运行测试验证通过**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_validators.py -v`
预期：5 passed。

- [ ] **步骤 5：Commit**

```bash
git add app/validators.py tests/test_validators.py
git commit -m "feat: 新增文件校验与解码模块"
```

---

## 任务 3：统计与风险 `app/stats.py`（TDD）

**文件：**
- 创建：`app/stats.py`
- 测试：`tests/test_stats.py`

- [ ] **步骤 1：编写失败的测试**

```python
from app import stats


def _d(label, conf=0.9):
    return {"category": stats.category_of(label), "label": label, "confidence": conf}


def test_category_mapping():
    assert stats.category_of("fire") == "fire"
    assert stats.category_of("smoke") == "smoke"
    assert stats.category_of("person") == "other"


def test_single_counts_and_risk_high():
    res = stats.compute_single([_d("fire"), _d("smoke")])
    assert res["counts"]["fire"] == 1
    assert res["counts"]["smoke"] == 1
    assert res["risk"] == "high"


def test_risk_medium_when_only_smoke():
    res = stats.compute_single([_d("smoke")])
    assert res["risk"] == "medium"


def test_risk_normal_when_empty():
    res = stats.compute_single([])
    assert res["risk"] == "normal"
    assert res["counts"]["total"] == 0


def test_task_stats_accumulate_and_peak():
    ts = stats.TaskStats()
    ts.accumulate([_d("fire"), _d("fire")])
    ts.accumulate([_d("smoke")])
    snap = ts.snapshot()
    assert snap["frames"] == 2
    assert snap["total"]["fire"] == 2
    assert snap["peak"]["fire"] == 2
    assert snap["total"]["smoke"] == 1
    assert snap["risk"] == "high"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_stats.py -v`
预期：FAIL（模块不存在）。

- [ ] **步骤 3：编写实现**

```python
from . import config


def category_of(label: str) -> str:
    low = (label or "").strip().lower()
    if low in config.FIRE_LABELS:
        return "fire"
    if low in config.SMOKE_LABELS:
        return "smoke"
    return "other"


def _empty_counts():
    return {"fire": 0, "smoke": 0, "other": 0, "total": 0}


def counts_from_detections(detections):
    counts = _empty_counts()
    for d in detections:
        cat = d.get("category", "other")
        if cat not in counts:
            cat = "other"
        counts[cat] += 1
        counts["total"] += 1
    return counts


def risk_level(fire, smoke):
    if fire > 0:
        return config.RISK_HIGH
    if smoke > 0:
        return config.RISK_MEDIUM
    return config.RISK_NORMAL


def compute_single(detections):
    counts = counts_from_detections(detections)
    return {"counts": counts, "risk": risk_level(counts["fire"], counts["smoke"])}


class TaskStats:
    def __init__(self):
        self.frames = 0
        self.total = _empty_counts()
        self.peak = _empty_counts()

    def accumulate(self, detections):
        counts = counts_from_detections(detections)
        self.frames += 1
        for key in self.total:
            self.total[key] += counts[key]
            self.peak[key] = max(self.peak[key], counts[key])

    def snapshot(self):
        return {
            "frames": self.frames,
            "total": dict(self.total),
            "peak": dict(self.peak),
            "risk": risk_level(self.total["fire"], self.total["smoke"]),
        }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_stats.py -v`
预期：5 passed。

- [ ] **步骤 5：Commit**

```bash
git add app/stats.py tests/test_stats.py
git commit -m "feat: 新增统计与风险分级模块"
```

---

## 任务 4：任务状态机 `app/tasks.py`（TDD）

**文件：**
- 创建：`app/tasks.py`
- 测试：`tests/test_tasks.py`

- [ ] **步骤 1：编写失败的测试**

```python
import threading
from app import tasks
from app.stats import TaskStats


def test_create_assigns_unique_ids():
    reg = tasks.TaskRegistry()
    a = reg.create("video")
    b = reg.create("video")
    assert a.id != b.id
    assert reg.get(a.id) is a


def test_initial_status_pending():
    reg = tasks.TaskRegistry()
    assert reg.create("video").status == tasks.PENDING


def test_request_stop_sets_event():
    reg = tasks.TaskRegistry()
    t = reg.create("video")
    t.status = tasks.RUNNING
    t.request_stop()
    assert t.stop_event.is_set()


def test_stream_paths_do_not_cover_each_other():
    """意图：新任务必须与旧任务隔离，旧任务结果不得覆盖新任务。"""
    reg = tasks.TaskRegistry()
    old = reg.create("video")
    new = reg.create("video")
    old.latest_jpeg = b"old-frame"
    new.latest_jpeg = b"new-frame"
    assert reg.get(old.id).latest_jpeg == b"old-frame"
    assert reg.get(new.id).latest_jpeg == b"new-frame"


def test_stats_bound_to_task():
    reg = tasks.TaskRegistry()
    t = reg.create("video")
    assert isinstance(t.stats, TaskStats)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_tasks.py -v`
预期：FAIL（模块不存在）。

- [ ] **步骤 3：编写实现**

```python
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

    def remove(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest tests/test_tasks.py -v`
预期：5 passed。

- [ ] **步骤 5：Commit**

```bash
git add app/tasks.py tests/test_tasks.py
git commit -m "feat: 新增任务状态机与任务表"
```

---

## 任务 5：模型加载与推理 `app/detector.py`

**文件：**
- 创建：`app/detector.py`

- [ ] **步骤 1：编写实现**

```python
import time

from ultralytics import YOLO

from . import config, stats


class ModelNotLoadedError(Exception):
    pass


class Detector:
    def __init__(self):
        self.model = None
        self.class_names = {}
        self.load_error = None

    def load(self, path=None):
        path = str(path or config.MODEL_PATH)
        try:
            self.model = YOLO(path)
            self.class_names = dict(getattr(self.model, "names", {}) or {})
            self.load_error = None
        except Exception as exc:  # noqa: BLE001
            self.model = None
            self.class_names = {}
            self.load_error = f"检测模型加载失败：{exc}"

    @property
    def ready(self) -> bool:
        return self.model is not None

    def infer(self, frame_bgr):
        if not self.ready:
            raise ModelNotLoadedError(self.load_error or "检测模型未加载")
        started = time.time()
        results = self.model.predict(
            frame_bgr, conf=config.CONF_THRESHOLD, verbose=False
        )
        detections = []
        annotated = frame_bgr
        for result in results:
            names = dict(getattr(result, "names", {}) or {})
            boxes = getattr(result, "boxes", None)
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    label = names.get(cls_id, str(cls_id))
                    x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                    detections.append(
                        {
                            "label": label,
                            "category": stats.category_of(label),
                            "confidence": round(float(box.conf[0]), 4),
                            "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                        }
                    )
            annotated = result.plot()
        elapsed_ms = int((time.time() - started) * 1000)
        return annotated, detections, elapsed_ms
```

- [ ] **步骤 2：冒烟验证模型可加载**

运行：`& "D:\miniconda\envs\aigc\python.exe" -c "from app.detector import Detector; d=Detector(); d.load(); print(d.ready, d.load_error, len(d.class_names))"`
预期：打印 `True None <类别数>`（占位模型为 80）。

- [ ] **步骤 3：Commit**

```bash
git add app/detector.py
git commit -m "feat: 新增 YOLO 模型加载与推理封装"
```

---

## 任务 6：图片检测接口 `app/routers/image.py`

**文件：**
- 创建：`app/routers/image.py`

- [ ] **步骤 1：编写实现**

```python
import base64
import time

import cv2
from fastapi import APIRouter, File, Request, UploadFile

from .. import stats, validators

router = APIRouter()


@router.post("/api/detect/image")
async def detect_image(request: Request, file: UploadFile = File(...)):
    detector = request.app.state.detector
    data = await file.read()
    validators.validate_image(file.filename, file.content_type, data)
    frame = validators.decode_image(data)

    annotated, detections, elapsed_ms = detector.infer(frame)
    ok, buf = cv2.imencode(".jpg", annotated)
    if not ok:
        encoded = ""
    else:
        encoded = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

    return {
        "image": encoded,
        "detections": detections,
        "stats": stats.compute_single(detections),
        "elapsed_ms": elapsed_ms,
        "detected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
```

- [ ] **步骤 2：Commit**

```bash
git add app/routers/image.py
git commit -m "feat: 新增图片检测接口"
```

---

## 任务 7：视频检测接口 `app/routers/video.py`

**文件：**
- 创建：`app/routers/video.py`

- [ ] **步骤 1：编写实现**

```python
import asyncio
import os
import threading

import cv2
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from .. import tasks, validators

router = APIRouter()

_BOUNDARY = "frame"


def _mime_chunk(jpeg: bytes) -> bytes:
    return (
        b"--" + _BOUNDARY.encode() + b"\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
    )


def _process_video(task, path, detector):
    task.status = tasks.RUNNING
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    delay = 1.0 / fps if fps > 0 else 0.04
    try:
        while not task.stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                break
            annotated, detections, _ = detector.infer(frame)
            task.stats.accumulate(detections)
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                task.set_frame(buf.tobytes())
            if task.stop_event.wait(delay):
                break
        task.status = tasks.STOPPED if task.stop_event.is_set() else tasks.DONE
    except Exception as exc:  # noqa: BLE001
        task.status = tasks.ERROR
        task.error = f"视频处理中断：{exc}"
    finally:
        cap.release()
        try:
            os.remove(path)
        except OSError:
            pass


@router.post("/api/detect/video")
async def create_video_task(request: Request, file: UploadFile = File(...)):
    detector = request.app.state.detector
    data = await file.read()
    validators.validate_video(file.filename, file.content_type, data)

    task = request.app.state.registry.create("video")
    task.source_name = file.filename
    path = validators.save_video_temp(data, file.filename)
    thread = threading.Thread(
        target=_process_video, args=(task, path, detector), daemon=True
    )
    thread.start()
    return {"task_id": task.id}


@router.get("/api/detect/video/status/{task_id}")
async def video_status(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})
    return task.status_payload()


@router.post("/api/detect/video/stop/{task_id}")
async def video_stop(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})
    task.request_stop()
    return {"task_id": task_id, "status": task.status}


@router.get("/api/detect/video/stream/{task_id}")
async def video_stream(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})

    async def generator():
        while True:
            with task.frame_lock:
                jpeg = task.latest_jpeg
            if jpeg is not None:
                yield _mime_chunk(jpeg)
            if task.status in tasks.TERMINAL:
                break
            await asyncio.sleep(0.03)
        yield b"--" + _BOUNDARY.encode() + b"--\r\n"

    return StreamingResponse(
        generator(), media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}"
    )
```

- [ ] **步骤 2：Commit**

```bash
git add app/routers/video.py
git commit -m "feat: 新增视频检测任务接口与 MJPEG 流"
```

---

## 任务 8：应用装配 `app/main.py`

**文件：**
- 创建：`app/main.py`

- [ ] **步骤 1：编写实现**

```python
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .detector import Detector, ModelNotLoadedError
from .routers import image, video
from .tasks import TaskRegistry
from .validators import ValidationError

app = FastAPI(title="火点/烟雾目标检测")


@app.on_event("startup")
async def _startup():
    detector = Detector()
    detector.load()
    app.state.detector = detector
    app.state.registry = TaskRegistry()


@app.exception_handler(ValidationError)
async def _validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=exc.code, content={"code": exc.code, "message": exc.message})


@app.exception_handler(ModelNotLoadedError)
async def _model_handler(request: Request, exc: ModelNotLoadedError):
    return JSONResponse(status_code=503, content={"code": 503, "message": str(exc)})


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"code": 500, "message": "服务器处理异常，请重试"}
    )


@app.get("/api/health")
async def health():
    detector = getattr(app.state, "detector", None)
    return {
        "model_ready": bool(detector and detector.ready),
        "model_error": getattr(detector, "load_error", None),
        "class_names": getattr(detector, "class_names", {}),
    }


@app.get("/")
async def index():
    return FileResponse(config.STATIC_DIR / "index.html")


app.include_router(image.router)
app.include_router(video.router)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
```

- [ ] **步骤 2：启动服务验证可用**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m uvicorn app.main:app --port 8000`
预期：启动无异常；另开终端访问 `http://localhost:8000/api/health` 返回 `model_ready: true`。

- [ ] **步骤 3：Commit**

```bash
git add app/main.py
git commit -m "feat: 装配 FastAPI 应用与异常处理"
```

---

## 任务 9：前端页面 `static/`

**文件：**
- 创建：`static/index.html`、`static/style.css`、`static/app.js`

- [ ] **步骤 1：编写 `static/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>火点/烟雾目标检测</title>
<link rel="stylesheet" href="/static/style.css" />
</head>
<body>
<header>
  <h1>火点 / 烟雾目标检测</h1>
  <p class="disclaimer">结果仅用于辅助识别，不替代人工复核与应急决策。</p>
</header>

<nav class="tabs">
  <button id="tab-image" class="tab active" data-mode="image">图片检测</button>
  <button id="tab-video" class="tab" data-mode="video">视频检测</button>
</nav>

<main>
  <section id="panel-image" class="panel">
    <input type="file" id="image-input" accept=".jpg,.jpeg,.png" />
    <button id="image-start">开始检测</button>
  </section>

  <section id="panel-video" class="panel hidden">
    <input type="file" id="video-input" accept=".mp4,.avi,.mov" />
    <button id="video-start">开始检测</button>
    <button id="video-stop" disabled>停止</button>
    <span id="video-status" class="badge">未开始</span>
  </section>

  <div id="message" class="message hidden"></div>

  <div class="result">
    <div class="viewer">
      <img id="preview" alt="检测结果预览" />
    </div>
    <aside class="side">
      <div id="risk" class="risk normal">风险等级：正常</div>
      <div id="summary" class="summary"></div>
      <h3>检测明细</h3>
      <table id="detections">
        <thead><tr><th>类别</th><th>置信度</th><th>位置</th></tr></thead>
        <tbody></tbody>
      </table>
    </aside>
  </div>
</main>

<script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **步骤 2：编写 `static/style.css`**

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: "Microsoft YaHei", system-ui, sans-serif; background: #f5f6f8; color: #1f2937; }
header { padding: 16px 24px; background: #111827; color: #fff; }
header h1 { margin: 0 0 4px; font-size: 20px; }
.disclaimer { margin: 0; font-size: 12px; color: #d1d5db; }
.tabs { display: flex; gap: 8px; padding: 16px 24px 0; }
.tab { padding: 8px 20px; border: 1px solid #d1d5db; background: #fff; border-radius: 6px; cursor: pointer; }
.tab.active { background: #2563eb; color: #fff; border-color: #2563eb; }
main { padding: 16px 24px 32px; }
.panel { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 12px 0; }
.panel.hidden, .hidden { display: none; }
button { padding: 8px 16px; border: none; background: #2563eb; color: #fff; border-radius: 6px; cursor: pointer; }
button:disabled { background: #9ca3af; cursor: not-allowed; }
.badge { padding: 4px 12px; border-radius: 12px; background: #e5e7eb; font-size: 13px; }
.message { margin: 12px 0; padding: 10px 14px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 6px; }
.result { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-top: 16px; }
.viewer { background: #000; border-radius: 8px; display: flex; align-items: center; justify-content: center; min-height: 320px; overflow: hidden; }
.viewer img { max-width: 100%; max-height: 70vh; }
.side { background: #fff; border-radius: 8px; padding: 16px; }
.risk { padding: 10px 14px; border-radius: 6px; font-weight: 600; margin-bottom: 12px; }
.risk.normal { background: #ecfdf5; color: #047857; }
.risk.medium { background: #fffbeb; color: #b45309; }
.risk.high { background: #fef2f2; color: #b91c1c; }
.summary { font-size: 13px; color: #374151; line-height: 1.9; margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 6px 8px; border-bottom: 1px solid #e5e7eb; text-align: left; }
```

- [ ] **步骤 3：编写 `static/app.js`**

```javascript
const $ = (id) => document.getElementById(id);
let mode = "image";
let currentTaskId = null;
let pollTimer = null;

function showMessage(text) {
  const el = $("message");
  if (!text) { el.classList.add("hidden"); el.textContent = ""; return; }
  el.textContent = text;
  el.classList.remove("hidden");
}

function switchMode(next) {
  mode = next;
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.mode === next)
  );
  $("panel-image").classList.toggle("hidden", next !== "image");
  $("panel-video").classList.toggle("hidden", next !== "video");
  if (next !== "video") stopVideoTask();
  $("preview").src = "";
  resetStats();
  showMessage("");
}

function resetStats() {
  $("risk").className = "risk normal";
  $("risk").textContent = "风险等级：正常";
  $("summary").textContent = "";
  $("detections").querySelector("tbody").innerHTML = "";
}

function renderRisk(risk) {
  const text = { normal: "正常", medium: "中风险", high: "高风险" }[risk] || risk;
  $("risk").className = "risk " + risk;
  $("risk").textContent = "风险等级：" + text;
}

function renderDetections(list) {
  const tbody = $("detections").querySelector("tbody");
  tbody.innerHTML = "";
  list.forEach((d) => {
    const tr = document.createElement("tr");
    const loc = d.bbox.map((v) => Math.round(v)).join(",");
    [`${d.label}(${d.category})`, d.confidence.toFixed(2), loc].forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

async function parseError(resp) {
  try {
    const data = await resp.json();
    const msg = data.message || (data.detail && data.detail.message) || "请求失败";
    return msg;
  } catch (e) {
    return "请求失败（" + resp.status + "）";
  }
}

$("image-start").onclick = async () => {
  const file = $("image-input").files[0];
  if (!file) { showMessage("请选择要检测的图片"); return; }
  showMessage("");
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch("/api/detect/image", { method: "POST", body: fd });
    if (!resp.ok) { showMessage(await parseError(resp)); return; }
    const data = await resp.json();
    $("preview").src = data.image;
    renderRisk(data.stats.risk);
    const c = data.stats.counts;
    $("summary").textContent =
      `火点：${c.fire}　烟雾：${c.smoke}　其它：${c.other}　合计：${c.total}　耗时：${data.elapsed_ms}ms　时间：${data.detected_at}`;
    renderDetections(data.detections);
  } catch (e) {
    showMessage("网络异常，请重试");
  }
};

$("video-start").onclick = async () => {
  const file = $("video-input").files[0];
  if (!file) { showMessage("请选择要检测的视频"); return; }
  showMessage("");
  stopVideoTask();
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch("/api/detect/video", { method: "POST", body: fd });
    if (!resp.ok) { showMessage(await parseError(resp)); return; }
    const data = await resp.json();
    currentTaskId = data.task_id;
    $("preview").src = `/api/detect/video/stream/${currentTaskId}`;
    $("video-stop").disabled = false;
    $("video-status").textContent = "检测中";
    pollTimer = setInterval(() => pollStatus(currentTaskId), 600);
  } catch (e) {
    showMessage("网络异常，请重试");
  }
};

$("video-stop").onclick = () => stopVideoTask();

async function stopVideoTask() {
  if (!currentTaskId) return;
  const id = currentTaskId;
  currentTaskId = null;
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  $("video-stop").disabled = true;
  try { await fetch(`/api/detect/video/stop/${id}`, { method: "POST" }); } catch (e) {}
}

async function pollStatus(id) {
  try {
    const resp = await fetch(`/api/detect/video/status/${id}`);
    if (!resp.ok) return;
    const s = await resp.json();
    if (id !== currentTaskId) return;  // 旧任务结果不得覆盖新任务
    $("video-status").textContent = s.status_text;
    renderRisk(s.stats.risk);
    const c = s.stats.total;
    const p = s.stats.peak;
    $("summary").textContent =
      `已处理帧：${s.stats.frames}　火点累计：${c.fire}（峰值${p.fire}）　烟雾累计：${c.smoke}（峰值${p.smoke}）　其它：${c.other}`;
    if (s.error) showMessage(s.error);
    if (["done", "stopped", "error"].includes(s.status)) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      $("video-stop").disabled = true;
      if (id === currentTaskId) currentTaskId = null;
    }
  } catch (e) {}
}

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => switchMode(t.dataset.mode);
});
```

- [ ] **步骤 4：Commit**

```bash
git add static
git commit -m "feat: 新增前端图片/视频检测页面"
```

---

## 任务 10：交付文档

**文件：**
- 创建：`README.md`

- [ ] **步骤 1：编写 README.md**

````markdown
# 火点/烟雾目标检测 Web 应用

## 环境
- 运行时：conda 环境 `aigc`（Python 3.12）
- 解释器路径：`D:\miniconda\envs\aigc\python.exe`
- 依赖：见 `requirements.txt`

## 安装依赖
```bash
& "D:\miniconda\envs\aigc\python.exe" -m pip install -r requirements.txt
```

## 模型
- 将已训练权重放入 `models/`，并在 `app/config.py` 中把 `MODEL_PATH` 指向该文件。
- 权重缺失时应用仍可启动，检测接口会返回 503 与可理解提示。

## 启动
```bash
& "D:\miniconda\envs\aigc\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 访问
浏览器打开 `http://localhost:8000`

## 测试
```bash
& "D:\miniconda\envs\aigc\python.exe" -m pytest -v
```

## 免责声明
检测结果仅用于辅助识别，不能替代人工复核和实际应急决策。
````

- [ ] **步骤 2：Commit**

```bash
git add README.md
git commit -m "docs: 新增部署与使用说明"
```

---

## 任务 11：端到端验证

**文件：** 无（验证任务）

- [ ] **步骤 1：运行全部单元测试**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m pytest -v`
预期：validators/stats/tasks 全部通过。

- [ ] **步骤 2：启动服务并验证健康检查**

运行：`& "D:\miniconda\envs\aigc\python.exe" -m uvicorn app.main:app --port 8000`
访问 `http://localhost:8000/api/health`，预期 `model_ready: true`。

- [ ] **步骤 3：图片检测验证（正向 + 反向）**

- 正向：上传一张含可识别目标的图片，页面显示标注图、明细与统计。
- 反向：上传 `.txt` 改名的假图片 → 提示「文件已损坏或无法读取」。
- 边界：上传 >10MB 图片 → 提示「图片文件过大」。

- [ ] **步骤 4：视频检测验证（正向 + 停止 + 模式切换）**

- 正向：上传短视频 → 画面实时刷新、状态显示「检测中」→ 播放结束状态变「已完成」。
- 停止：检测中点「停止」→ 状态变「已停止」，统计保留。
- 模式切换：视频运行中切到图片模式 → 视频任务停止，图片结果正常。
- 隔离：视频 A 运行中启动视频 B → 画面与统计只反映 B，不被 A 覆盖。

- [ ] **步骤 5：异常恢复验证**

- 模型加载失败场景：临时把 `MODEL_PATH` 指向不存在文件启动 → 启动不崩溃，检测接口返回 503 中文提示。

- [ ] **步骤 6：最终提交**

```bash
git add -A
git commit -m "test: 完成端到端验证"
```

---

## 需求覆盖对照

| 能力要求 | 覆盖任务 |
|---|---|
| 1 媒体输入与检测 | 任务 2、5、6、7 |
| 2 检测结果展示 | 任务 5（标注+明细）、9（前端渲染） |
| 3 统计与告警 | 任务 3、6、7、9 |
| 4 视频任务管理 | 任务 4、7、9 |
| 5 异常反馈与恢复 | 任务 2、8、11 |
| 6 工程交付 | 任务 0、10 |

## 安全覆盖对照

| 规则 | 覆盖 |
|---|---|
| SEC-03/13 输入校验与资源上限 | 任务 2（扩展名/MIME/大小/解码）、config 上限 |
| SEC-04 输出最小化 | 任务 6/7 返回固定字段，不含路径与堆栈 |
| SEC-01 鉴权豁免 | 本地单机工具，已在设计文档显式声明 |
| SEC-10 日志安全 | 仅记录 task_id 与文件名，无绝对路径明文 |

## 已知问题

- `权重.pt` 当前为 0 字节空文件；本计划用占位模型 `yolov8n.pt` 跑通链路，权重到位后替换 `config.MODEL_PATH` 并重新验证类别名映射与配色。
