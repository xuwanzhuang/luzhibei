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
