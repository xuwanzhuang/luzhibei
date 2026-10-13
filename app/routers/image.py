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
