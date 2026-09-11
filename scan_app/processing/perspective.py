"""Scan tài liệu: sắp 4 góc → tính kích thước → tạo ma trận → biến đổi ảnh."""
import time
import cv2
import numpy as np
from . import PERSPECTIVE_INTERPOLATIONS, BORDER_MODES, validate_image, check_size, choice


def order_points(points):
    """Trả về bốn góc theo thứ tự: trên trái, trên phải, dưới phải, dưới trái."""
    points = np.asarray(points, dtype=np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError('Hãy chọn đúng 4 góc tài liệu.')

    # Hull có 4 đỉnh nghĩa là các điểm khác nhau và tạo tứ giác lồi.
    hull = cv2.convexHull(points).reshape(-1, 2)
    if len(hull) != 4 or abs(cv2.contourArea(hull)) < 1:
        raise ValueError('Bốn góc phải khác nhau và tạo tứ giác lồi, không thẳng hàng.')
    edges = np.roll(hull, -1, axis=0) - hull
    diagonals = np.roll(hull, -2, axis=0) - hull
    cross_product = edges[:, 0] * diagonals[:, 1] - edges[:, 1] * diagonals[:, 0]
    heights = np.abs(cross_product) / np.linalg.norm(edges, axis=1)
    if heights.min() < 0.5:
        raise ValueError('Các góc gần thẳng hàng; hãy chọn lại vùng tài liệu.')

    # Tổng x+y tìm góc trên trái/dưới phải; hiệu y-x tìm hai góc còn lại.
    coordinate_sum = points.sum(axis=1)
    coordinate_diff = points[:, 1] - points[:, 0]
    ordered = points[[np.argmin(coordinate_sum), np.argmin(coordinate_diff),
                      np.argmax(coordinate_sum), np.argmax(coordinate_diff)]]
    if len(np.unique(ordered, axis=0)) == 4 and cv2.isContourConvex(ordered):
        return ordered

    # Với hình thoi, sum/diff có thể chọn trùng góc. Hull đã xếp quanh viền;
    # chỉ cần đưa góc có tổng nhỏ nhất lên đầu (nếu bằng nhau, lấy góc trên).
    first = min(range(4), key=lambda i: (hull[i].sum(), hull[i, 1]))
    return np.roll(hull, -first, axis=0)


def compute_output_size(src_points):
    """Tính rộng/cao từ bốn góc đã được order_points() sắp xếp."""
    src_points = np.asarray(src_points, dtype=np.float32)
    top_left, top_right, bottom_right, bottom_left = src_points
    top_width = np.linalg.norm(top_right - top_left)
    bottom_width = np.linalg.norm(bottom_right - bottom_left)
    left_height = np.linalg.norm(bottom_left - top_left)
    right_height = np.linalg.norm(bottom_right - top_right)
    width = max(2, int(round(max(top_width, bottom_width))))
    height = max(2, int(round(max(left_height, right_height))))
    return width, height


def perspective_transform(image, points, output_width=None, output_height=None,
                          interpolation='Linear', border_mode='Constant', border_value=(255, 255, 255)):
    """Trả về ảnh, ma trận, góc nguồn/đích và thời gian warp (ms)."""
    validate_image(image)
    src_points = order_points(points)
    image_height, image_width = image.shape[:2]
    if (src_points < 0).any() or (src_points[:, 0] > image_width - 1).any() or (src_points[:, 1] > image_height - 1).any():
        raise ValueError('Các góc phải nằm trong ảnh đầu vào.')

    width, height = compute_output_size(src_points)
    if output_width is not None:
        width = output_width
    if output_height is not None:
        height = output_height
    # Cần ít nhất 2 pixel mỗi chiều để bốn góc đích không trùng nhau.
    width, height = check_size(width, height, minimum=2)
    dst_points = np.float32([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1],
    ])

    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
        raise ValueError('Không thể biến đổi vùng này; hãy chọn lại bốn góc.')
    start = time.perf_counter()
    result = cv2.warpPerspective(
        image, matrix, (width, height),
        flags=choice(PERSPECTIVE_INTERPOLATIONS, interpolation),
        borderMode=choice(BORDER_MODES, border_mode), borderValue=border_value,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, matrix, src_points, dst_points, elapsed_ms


def reprojection_error(src_points, dst_points, matrix):
    """Kiểm tra ma trận đưa bốn góc nguồn tới gần bốn góc đích đến mức nào."""
    src_points = np.asarray(src_points, dtype=np.float32).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(src_points, matrix).reshape(-1, 2)
    return projected, np.linalg.norm(projected - dst_points, axis=1)
