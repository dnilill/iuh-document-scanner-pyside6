"""Chọn/sắp bốn góc, Perspective Transform và đánh giá từ notebook."""
import time
import cv2
import numpy as np
from . import (PERSPECTIVE_INTERPOLATIONS, BORDER_MODES, validate_image,
               check_size, choice, gray, laplacian_variance)


def order_points(pts):
    """Notebook Perspective cell 7; giữ sum/diff nếu hợp lệ, sửa trường hợp trùng."""
    pts = np.asarray(pts, dtype=np.float32)
    if pts.shape != (4, 2) or not np.isfinite(pts).all():
        raise ValueError('Cần đúng 4 điểm (x, y) hữu hạn.')
    hull = cv2.convexHull(pts).reshape(-1, 2)
    if len(hull) != 4 or abs(cv2.contourArea(hull)) < 1:
        raise ValueError('Bốn góc phải khác nhau và tạo tứ giác lồi, không thẳng hàng.')
    edges = np.roll(hull, -1, axis=0) - hull
    diagonals = np.roll(hull, -2, axis=0) - hull
    # Chiều cao quá nhỏ nghĩa là ba góc gần nằm trên một đường thẳng.
    cross_product = edges[:, 0] * diagonals[:, 1] - edges[:, 1] * diagonals[:, 0]
    altitudes = np.abs(cross_product) / np.linalg.norm(edges, axis=1)
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
    # tl/tr/br/bl: trên trái, trên phải, dưới phải, dưới trái.
    top_width = np.linalg.norm(tr - tl)
    bottom_width = np.linalg.norm(br - bl)
    left_height = np.linalg.norm(bl - tl)
    right_height = np.linalg.norm(br - tr)
    # Lấy cạnh dài hơn, giữ quy ước notebook (không cộng thêm 1 pixel).
    width = max(2, int(round(max(top_width, bottom_width))))
    height = max(2, int(round(max(left_height, right_height))))
    return width, height


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
    # Bốn góc tài liệu được đưa về bốn góc hình chữ nhật đầu ra.
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


def polygon_area(points):
    p = order_points(points)
    x, y = p[:, 0], p[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def reprojection_error(src_pts, dst_pts, H):
    src = order_points(src_pts).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(src, H).reshape(-1, 2)
    return projected, np.linalg.norm(projected - dst_pts, axis=1)


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
