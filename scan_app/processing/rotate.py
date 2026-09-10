"""Rotate với canvas keep-full, giữ nguyên thuật toán đã kiểm thử."""
import math
import cv2
import numpy as np
from . import PERSPECTIVE_INTERPOLATIONS, BORDER_MODES, validate_image, check_size, choice


def rotate_image(img, angle=0, scale=1.0, keep_full=True,
                 interpolation='Linear', border_mode='Constant', border_value=(255, 255, 255)):
    """Notebook Resize cell 12; sửa canvas và tâm pixel để không mất mép."""
    validate_image(img)
    if not np.isfinite(angle) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('Góc phải hữu hạn; scale phải hữu hạn và > 0.')
    h, w = img.shape[:2]
    center = ((w - 1) / 2, (h - 1) / 2)
    M = cv2.getRotationMatrix2D(center, float(angle), float(scale))
    if keep_full:
        cos, sin = abs(M[0, 0]), abs(M[0, 1])
        new_w = max(1, math.ceil(h * sin + w * cos - 1e-10))
        new_h = max(1, math.ceil(h * cos + w * sin - 1e-10))
        M[0, 2] += (new_w - 1) / 2 - center[0]
        M[1, 2] += (new_h - 1) / 2 - center[1]
    else:
        new_w, new_h = w, h
    size = check_size(new_w, new_h)
    return cv2.warpAffine(img, M, size, flags=choice(PERSPECTIVE_INTERPOLATIONS, interpolation),
                          borderMode=choice(BORDER_MODES, border_mode), borderValue=border_value)
