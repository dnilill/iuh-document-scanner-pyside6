"""Refactor từ hai notebook của nhóm. Xem docs/THAY_DOI.md.

Giữ cv2.resize, getRotationMatrix2D/warpAffine và
getPerspectiveTransform/warpPerspective cùng các phép đo gốc.
Ảnh API: uint8, grayscale hoặc BGR. Tọa độ theo ảnh, không theo widget.
"""
import math
import time
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

INTERPOLATIONS = {
    'Nearest': cv2.INTER_NEAREST, 'Linear': cv2.INTER_LINEAR,
    'Cubic': cv2.INTER_CUBIC, 'Lanczos4': cv2.INTER_LANCZOS4,
    'Area': cv2.INTER_AREA,
}
PERSPECTIVE_INTERPOLATIONS = {k: v for k, v in INTERPOLATIONS.items() if k != 'Area'}
BORDER_MODES = {'Constant': cv2.BORDER_CONSTANT, 'Replicate': cv2.BORDER_REPLICATE,
                'Reflect': cv2.BORDER_REFLECT}
MAX_PIXELS = 24_000_000


def validate_image(image):
    if not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError('Ảnh đầu vào rỗng hoặc không hợp lệ.')
    if image.dtype != np.uint8 or not (image.ndim == 2 or
            (image.ndim == 3 and image.shape[2] == 3)):
        raise ValueError('Cần ảnh uint8 grayscale hoặc BGR 3 kênh.')
    check_size(image.shape[1], image.shape[0])


def check_size(width, height, minimum=1):
    for value in (width, height):
        if value is None or not np.isfinite(value) or int(value) != value or value < minimum:
            raise ValueError(f'Chiều rộng/cao phải là số nguyên ≥ {minimum}.')
    if width * height > MAX_PIXELS:
        raise ValueError('Ảnh vượt giới hạn 24 megapixel; hãy giảm kích thước.')
    return int(width), int(height)


def choice(mapping, name):
    if name not in mapping:
        raise ValueError(f'Tham số không hợp lệ: {name}.')
    return mapping[name]


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
            ratio = min(v / original for v, original in ((width, w), (height, h))
                        if v is not None)
            new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
        else:
            new_w, new_h = width, height
    size = check_size(new_w, new_h)
    return cv2.resize(img, size, interpolation=choice(INTERPOLATIONS, interpolation))


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


def order_points(pts):
    """Notebook Perspective cell 7; giữ sum/diff nếu hợp lệ, sửa trường hợp trùng."""
    pts = np.asarray(pts, dtype=np.float32)
    if pts.shape != (4, 2) or not np.isfinite(pts).all():
        raise ValueError('Cần đúng 4 điểm (x, y) hữu hạn.')
    hull = cv2.convexHull(pts).reshape(-1, 2)
    if len(hull) != 4 or abs(cv2.contourArea(hull)) < 1:
        raise ValueError('Bốn góc phải khác nhau và tạo tứ giác lồi, không thẳng hàng.')
    edges = np.roll(hull, -1, axis=0) - hull
    altitudes = np.abs(edges[:, 0] * (np.roll(hull, -2, axis=0) - hull)[:, 1]
                       - edges[:, 1] * (np.roll(hull, -2, axis=0) - hull)[:, 0]) / np.linalg.norm(edges, axis=1)
    if altitudes.min() < 0.5:
        raise ValueError('Các góc gần thẳng hàng; hãy chọn lại vùng tài liệu.')
    s, diff = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
    rect = pts[[np.argmin(s), np.argmin(diff), np.argmax(s), np.argmax(diff)]]
    if len(np.unique(rect, axis=0)) == 4 and cv2.isContourConvex(rect):
        return rect.copy()
    # Chỉ dùng fallback khi sum/diff chọn trùng góc; không đổi thuật toán warp.
    center = pts.mean(axis=0)
    rect = pts[np.argsort(np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0]))]
    first = min(range(4), key=lambda i: (float(rect[i].sum()), float(rect[i, 1]), float(rect[i, 0])))
    return np.roll(rect, -first, axis=0).copy()


def compute_output_size(rect):
    tl, tr, br, bl = order_points(rect)
    # Giữ quy ước độ dài cạnh của notebook (không cộng thêm 1 pixel).
    return (max(2, int(round(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl))))),
            max(2, int(round(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr))))))


def perspective_transform(image, src_points, output_width=None, output_height=None,
                          interpolation='Linear', border_mode='Constant', border_value=(255, 255, 255)):
    """Notebook Perspective cell 11; cùng tuple kết quả và phạm vi đo warp."""
    validate_image(image)
    rect = order_points(src_points)
    h, w = image.shape[:2]
    if (rect < 0).any() or (rect[:, 0] > w-1).any() or (rect[:, 1] > h-1).any():
        raise ValueError('Các góc phải nằm trong ảnh đầu vào.')
    auto_w, auto_h = compute_output_size(rect)
    out_w, out_h = check_size(auto_w if output_width is None else output_width,
                              auto_h if output_height is None else output_height, minimum=2)
    dst = np.array([[0, 0], [out_w-1, 0], [out_w-1, out_h-1], [0, out_h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(rect, dst)
    if not np.isfinite(M).all() or np.linalg.matrix_rank(M) < 3:
        raise ValueError('Ma trận phối cảnh suy biến; hãy chọn lại bốn góc.')
    t0 = time.perf_counter()
    warped = cv2.warpPerspective(image, M, (out_w, out_h),
        flags=choice(PERSPECTIVE_INTERPOLATIONS, interpolation),
        borderMode=choice(BORDER_MODES, border_mode), borderValue=border_value)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return warped, M, rect, dst, elapsed_ms


def gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def laplacian_variance(image):
    return float(cv2.Laplacian(gray(image), cv2.CV_64F).var())


def polygon_area(points):
    p = order_points(points)
    x, y = p[:, 0], p[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def reprojection_error(src_pts, dst_pts, H):
    src = order_points(src_pts).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(src, H).reshape(-1, 2)
    return projected, np.linalg.norm(projected - dst_pts, axis=1)


def mse(img1, img2):
    if img1.shape != img2.shape:
        raise ValueError('Hai ảnh đánh giá phải cùng kích thước và số kênh.')
    return float(np.mean((img1.astype(np.float32) - img2.astype(np.float32)) ** 2))


def psnr(img1, img2):
    m = mse(img1, img2)
    return float('inf') if m == 0 else float(10 * np.log10(255.0 ** 2 / m))


def ssim_global(img1, img2):
    """SSIM global đơn giản của notebook Perspective, khác SSIM cửa sổ."""
    if img1.shape != img2.shape:
        raise ValueError('Hai ảnh đánh giá phải cùng kích thước và số kênh.')
    g1, g2 = gray(img1).astype(np.float64), gray(img2).astype(np.float64)
    mu1, mu2 = g1.mean(), g2.mean()
    var1, var2 = g1.var(), g2.var()
    cov12 = ((g1-mu1)*(g2-mu2)).mean()
    C1, C2 = (0.01*255)**2, (0.03*255)**2
    return float(((2*mu1*mu2+C1)*(2*cov12+C2)) /
                 ((mu1**2+mu2**2+C1)*(var1+var2+C2)))


def evaluate_resize(original, resized):
    """Notebook Resize cell 14: đánh giá resize rồi hồi kích thước bằng Linear."""
    h, w = original.shape[:2]
    back = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LINEAR)
    a, b = gray(original), gray(back)
    win = min(7, h, w)
    win -= 1 - win % 2
    score = float(ssim(a, b, data_range=255, win_size=win)) if win >= 3 else None
    return {'MSE': round(mse(a, b), 3), 'PSNR (dB)': round(psnr(a, b), 3),
            'SSIM (cửa sổ)': None if score is None else round(score, 4),
            'Kích thước gốc': f'{w}×{h}',
            'Kích thước mới': f'{resized.shape[1]}×{resized.shape[0]}'}


def scan_perspective(image, points, interpolation='Linear', border_mode='Constant',
                     output_width=None, output_height=None, border_value=(255, 255, 255)):
    result, M, src, dst, t = perspective_transform(image, points, output_width,
        output_height, interpolation, border_mode, border_value)
    _, err = reprojection_error(src, dst, M)
    info = {'matrix': M, 'src_points': src, 'dst_points': dst,
            'output_width': result.shape[1], 'output_height': result.shape[0],
            'processing_time_ms': t, 'sharpness': laplacian_variance(result),
            'selected_area': polygon_area(src),
            'selected_area_ratio': polygon_area(src) / (image.shape[0]*image.shape[1]),
            'reprojection_mean_px': float(err.mean()), 'reprojection_max_px': float(err.max())}
    return result, info
