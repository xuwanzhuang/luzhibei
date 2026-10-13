import io
import numpy as np
import cv2
import pytest
from app import validators
from app.validators import ValidationError


def _png_bytes():
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_valid_image_passes():
    validators.validate_image("a.png", "image/png", _png_bytes())


def test_bad_extension_rejected():
    with pytest.raises(ValidationError) as e:
        validators.validate_image("a.txt", "text/plain", b"x")
    assert "类型" in e.value.message


def test_oversize_image_rejected():
    with pytest.raises(ValidationError):
        validators.validate_image("a.png", "image/png", b"0" * (11 * 1024 * 1024))


def test_undecodable_image_rejected():
    with pytest.raises(ValidationError) as e:
        validators.validate_image("a.png", "image/png", b"not-an-image")
    assert "读取" in e.value.message or "损坏" in e.value.message


def test_decode_image_returns_array():
    frame = validators.decode_image(_png_bytes())
    assert frame.shape[0] == 32 and frame.shape[1] == 32
