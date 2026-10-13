import asyncio
import threading

import cv2
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from .. import config, tasks
from ..validators import ValidationError

router = APIRouter()

CAMERA_ERROR_OPEN = "无法打开摄像头，请确认设备存在且未被占用"
CAMERA_ERROR_READ = "摄像头画面读取失败，设备可能已断开"

_BOUNDARY = "frame"


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


def _mime_chunk(jpeg: bytes) -> bytes:
    return (
        b"--" + _BOUNDARY.encode() + b"\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
    )


@router.post("/api/detect/camera/start")
async def start_camera(request: Request, device: str = Query(default=None)):
    parsed = parse_device(device)
    registry = request.app.state.registry
    if registry.active_of("camera") is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": 409, "message": "摄像头正在使用中，请先停止当前摄像头任务"},
        )
    task = registry.create("camera")
    task.source_name = f"摄像头 {parsed}"
    thread = threading.Thread(
        target=_process_camera,
        args=(task, parsed, request.app.state.detector),
        daemon=True,
    )
    thread.start()
    return {"task_id": task.id}


@router.get("/api/detect/camera/status/{task_id}")
async def camera_status(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})
    return task.status_payload()


@router.post("/api/detect/camera/stop/{task_id}")
async def camera_stop(request: Request, task_id: str):
    task = request.app.state.registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "任务不存在或已结束"})
    task.request_stop()
    return {"task_id": task_id, "status": task.status}


@router.get("/api/detect/camera/stream/{task_id}")
async def camera_stream(request: Request, task_id: str):
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
