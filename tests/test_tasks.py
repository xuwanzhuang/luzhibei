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
