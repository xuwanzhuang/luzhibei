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
