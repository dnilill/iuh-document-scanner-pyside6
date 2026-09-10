# Reference copied verbatim from notebook; only used for regression tests.
import cv2
import numpy as np
import time
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr


INTERPOLATIONS = {
    "Nearest": cv2.INTER_NEAREST,
    "Linear": cv2.INTER_LINEAR,
    "Cubic": cv2.INTER_CUBIC,
    "Lanczos4": cv2.INTER_LANCZOS4,
    "Area": cv2.INTER_AREA,
}

def resize_image(img, width=None, height=None, scale=None,
                  interpolation="Linear", keep_aspect_ratio=True):
    """
    Resize ảnh theo scale hoặc theo width/height cụ thể.
    - scale: hệ số phóng to/thu nhỏ (vd 0.5, 2.0). Nếu có -> ưu tiên dùng scale.
    - width, height: kích thước đích (pixel). Nếu keep_aspect_ratio=True và
      chỉ cung cấp 1 trong 2 -> tự tính giá trị còn lại theo tỉ lệ gốc.
    """
    h, w = img.shape[:2]
    interp = INTERPOLATIONS[interpolation]

    if scale is not None:
        new_w, new_h = int(w * scale), int(h * scale)
    else:
        if keep_aspect_ratio:
            if width and not height:
                new_w = width
                new_h = int(h * (width / w))
            elif height and not width:
                new_h = height
                new_w = int(w * (height / h))
            else:
                new_w, new_h = width, height
        else:
            new_w, new_h = width, height

    new_w, new_h = max(1, new_w), max(1, new_h)
    resized = cv2.resize(img, (new_w, new_h), interpolation=interp)
    return resized

def rotate_image(img, angle=0, scale=1.0, keep_full=True):
    """
    Xoay ảnh quanh tâm.
    - angle: góc xoay theo độ; dương = ngược chiều kim đồng hồ.
    - scale: hệ số phóng to/thu nhỏ khi xoay.
    - keep_full=True: tự mở rộng canvas để giữ toàn bộ ảnh sau khi xoay.
    """
    h, w = img.shape[:2]
    center = (w / 2, h / 2)

    # Ma trận xoay
    M = cv2.getRotationMatrix2D(center, angle, scale)

    if keep_full:
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])

        # Kích thước canvas mới để không cắt ảnh
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # Dịch tâm ảnh sang tâm canvas mới
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
    else:
        new_w, new_h = w, h

    rotated = cv2.warpAffine(
        img, M, (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )
    return rotated

def evaluate_resize(original, resized):
    h, w = original.shape[:2]
    back_to_original_size = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LINEAR)

    gray1 = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(back_to_original_size, cv2.COLOR_BGR2GRAY)

    mse_val = np.mean((gray1.astype("float") - gray2.astype("float")) ** 2)
    psnr_val = psnr(gray1, gray2, data_range=255)
    ssim_val = ssim(gray1, gray2, data_range=255)

    return {
        "MSE": round(mse_val, 3),
        "PSNR (dB)": round(psnr_val, 3),
        "SSIM": round(ssim_val, 4),
        "Kích thước gốc": f"{w}x{h}",
        "Kích thước mới": f"{resized.shape[1]}x{resized.shape[0]}"
    }
