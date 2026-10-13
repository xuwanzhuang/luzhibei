import pytest

from app import tasks
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
