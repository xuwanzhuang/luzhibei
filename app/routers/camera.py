from .. import config
from ..validators import ValidationError


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
