import threading

import cv2

from .. import config, tasks
from ..validators import ValidationError

CAMERA_ERROR_OPEN = "无法打开摄像头，请确认设备存在且未被占用"
CAMERA_ERROR_READ = "摄像头画面读取失败，设备可能已断开"


def parse_device(raw):
    if raw is None or str(raw).strip() == "":
        return config.CAMERA_DEVICE_DEFAULT
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValidationError(
            400, f"摄像头设备号不合法，取值范围 0~{config.CAMERA_MAX_DEVICE}"
        )
    if value < 0 or value > config.CAMERA_MAX_DEVICE:
        raise ValidationError(
            400, f"摄像头设备号不合法，取值范围 0~{config.CAMERA_MAX_DEVICE}"
        )
    return value


def _process_camera(task, device, detector):
    cap = cv2.VideoCapture(device)
    try:
        if not cap.isOpened():
            task.status = tasks.ERROR
            task.error = CAMERA_ERROR_OPEN
            return
        task.status = tasks.RUNNING
        delay = 1.0 / config.CAMERA_TARGET_FPS
        while not task.stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                task.status = tasks.ERROR
                task.error = CAMERA_ERROR_READ
                return
            annotated, detections, _ = detector.infer(frame)
            task.stats.accumulate(detections)
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                task.set_frame(buf.tobytes())
            if task.stop_event.wait(delay):
                break
        task.status = tasks.STOPPED
    except Exception:  # noqa: BLE001
        task.status = tasks.ERROR
        task.error = "摄像头处理中断，请重试"
    finally:
        cap.release()
