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
        except Exception:  # noqa: BLE001
            self.model = None
            self.class_names = {}
            self.load_error = "检测模型加载失败，请确认模型权重已正确放置"

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
