import os
import tempfile

import cv2
import numpy as np

from . import config


class ValidationError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _ext(filename):
    return os.path.splitext(filename or "")[1].lower()


def _check_ext(filename, allowed, kind):
    if _ext(filename) not in allowed:
        raise ValidationError(400, f"不支持的文件类型，{kind}仅支持：{', '.join(sorted(allowed))}")


def _check_mime(content_type, allowed):
    ct = (content_type or "").lower()
    if ct in config.OCTET_STREAM:
        return
    if ct not in allowed:
        raise ValidationError(400, f"不支持的文件类型：{ct}")


def _check_size(size, maximum, kind):
    if size > maximum:
        raise ValidationError(413, f"{kind}文件过大，上限 {maximum // (1024 * 1024)}MB")


def validate_image(filename, content_type, data):
    _check_ext(filename, config.IMAGE_EXTS, "图片")
    _check_mime(content_type, config.IMAGE_MIME)
    _check_size(len(data), config.MAX_IMAGE_BYTES, "图片")
    _check_decodable_image(data)


def _check_decodable_image(data):
    if not data:
        raise ValidationError(400, "文件内容为空，无法读取")
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValidationError(400, "文件已损坏或无法读取，请更换文件")


def decode_image(data):
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValidationError(400, "文件已损坏或无法读取，请更换文件")
    return frame


def validate_video(filename, content_type, data):
    _check_ext(filename, config.VIDEO_EXTS, "视频")
    _check_mime(content_type, config.VIDEO_MIME)
    _check_size(len(data), config.MAX_VIDEO_BYTES, "视频")
    if not data:
        raise ValidationError(400, "文件内容为空，无法读取")
    tmp = _write_temp(data, _ext(filename))
    try:
        cap = cv2.VideoCapture(tmp)
        if not cap.isOpened():
            raise ValidationError(400, "视频文件已损坏或无法读取，请更换文件")
        ok, _ = cap.read()
        cap.release()
        if not ok:
            raise ValidationError(400, "视频没有可读取的画面，请更换文件")
    finally:
        _safe_remove(tmp)


def save_video_temp(data, filename):
    return _write_temp(data, _ext(filename))


def _write_temp(data, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass
