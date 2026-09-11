"""Resize và đánh giá hồi kích thước từ notebook của nhóm."""
import cv2
from skimage.metrics import structural_similarity as ssim
import numpy as np
from . import INTERPOLATIONS, validate_image, check_size, choice, gray, mse, psnr


def resize_image(img, width=None, height=None, scale=None,
                 interpolation='Linear', keep_aspect_ratio=True):
    """Notebook Resize cell 10. Khi khóa tỷ lệ, W/H là hộp giới hạn."""
    validate_image(img)
    h, w = img.shape[:2]
    if scale is not None:
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError('Scale phải hữu hạn và > 0.')
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    else:
        if width is None and height is None:
            raise ValueError('Hãy nhập scale hoặc kích thước đích.')
        for value in (width, height):
            if value is not None:
                check_size(value, 1)
        if keep_aspect_ratio:
            # Nếu nhập cả hai chiều, lấy tỷ lệ nhỏ hơn để ảnh vừa khung.
            if width is None:
                ratio = height / h
            elif height is None:
                ratio = width / w
            else:
                ratio = min(width / w, height / h)
            new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
        else:
            new_w, new_h = width, height
    size = check_size(new_w, new_h)
    return cv2.resize(img, size, interpolation=choice(INTERPOLATIONS, interpolation))


def evaluate_resize(original, resized):
    """Notebook Resize cell 14: đánh giá resize rồi hồi kích thước bằng Linear."""
    h, w = original.shape[:2]
    back = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LINEAR)
    a, b = gray(original), gray(back)
    win = min(7, h, w)
    if win % 2 == 0:
        win -= 1  # SSIM cần kích thước cửa sổ lẻ.
    score = float(ssim(a, b, data_range=255, win_size=win)) if win >= 3 else None
    return {'MSE': round(mse(a, b), 3), 'PSNR (dB)': round(psnr(a, b), 3),
            'SSIM (cửa sổ)': None if score is None else round(score, 4),
            'Kích thước gốc': f'{w}×{h}',
            'Kích thước mới': f'{resized.shape[1]}×{resized.shape[0]}'}
