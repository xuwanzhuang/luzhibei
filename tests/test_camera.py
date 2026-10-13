import threading
import time

import numpy as np
import pytest

from app import tasks
from app.routers import camera
from app.validators import ValidationError


def test_active_of_returns_non_terminal_task():
    reg = tasks.TaskRegistry()
    camera_task = reg.create("camera")
    camera_task.status = tasks.RUNNING
    assert reg.active_of("camera") is camera_task
    assert reg.active_of("video") is None


def test_active_of_ignores_terminal_task():
    reg = tasks.TaskRegistry()
    camera_task = reg.create("camera")
    camera_task.status = tasks.STOPPED
    assert reg.active_of("camera") is None


def test_parse_device_default_when_missing():
    assert camera.parse_device(None) == 0
    assert camera.parse_device("") == 0


def test_parse_device_valid_value():
    assert camera.parse_device("3") == 3
    assert camera.parse_device(str(camera.config.CAMERA_MAX_DEVICE)) == camera.config.CAMERA_MAX_DEVICE


@pytest.mark.parametrize("bad", ["-1", "10", "abc", "1.5"])
def test_parse_device_rejects_invalid(bad):
    with pytest.raises(ValidationError) as e:
        camera.parse_device(bad)
    assert "设备号" in e.value.message


class FakeCapture:
    def __init__(self, opened=True, frames=1000):
        self._opened = opened
        self._frames = frames
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        if self._frames <= 0:
            return False, None
        self._frames -= 1
        return True, np.zeros((8, 8, 3), dtype=np.uint8)

    def release(self):
        self.released = True


class FakeDetector:
    def infer(self, frame):
        return frame, [], 0


def test_process_camera_open_failure(monkeypatch):
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda d: FakeCapture(opened=False))
    task = tasks.Task("camera")
    camera._process_camera(task, 0, FakeDetector())
    assert task.status == tasks.ERROR
    assert task.error == camera.CAMERA_ERROR_OPEN


def test_process_camera_read_failure(monkeypatch):
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda d: FakeCapture(opened=True, frames=0))
    task = tasks.Task("camera")
    camera._process_camera(task, 0, FakeDetector())
    assert task.status == tasks.ERROR
    assert task.error == camera.CAMERA_ERROR_READ


def test_process_camera_collects_frames_then_releases(monkeypatch):
    fake = FakeCapture(opened=True, frames=1000)
    monkeypatch.setattr(camera.cv2, "VideoCapture", lambda d: fake)
    task = tasks.Task("camera")
    thread = threading.Thread(target=camera._process_camera, args=(task, 0, FakeDetector()))
    thread.start()
    for _ in range(300):
        if task.stats.frames >= 3:
            break
        time.sleep(0.01)
    task.request_stop()
    thread.join(timeout=5)
    assert task.status == tasks.STOPPED
    assert task.stats.frames >= 3
    assert task.latest_jpeg is not None
    assert fake.released is True
