"""Đọc/ghi ảnh với đường dẫn Unicode trên Windows."""
from pathlib import Path
import cv2
import numpy as np
from .algorithms import validate_image


def read_image(path):
    raw = np.fromfile(Path(path), dtype=np.uint8)
    if not raw.size:
        raise ValueError('Tệp ảnh rỗng.')
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    validate_image(image)
    return image


def write_image(path, image):
    validate_image(image)
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}:
        raise ValueError('Định dạng lưu hỗ trợ: PNG, JPEG, BMP, TIFF.')
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise OSError('Không mã hóa được ảnh kết quả.')
    path.write_bytes(encoded.tobytes())
