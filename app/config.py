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

CAMERA_DEVICE_DEFAULT = 0
CAMERA_MAX_DEVICE = 9
CAMERA_TARGET_FPS = 15

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
