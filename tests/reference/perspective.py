# Reference copied verbatim from notebook; only used for regression tests.
import cv2
import numpy as np
import time
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr


def order_points(pts):
    pts = np.asarray(pts, dtype=np.float32)

    if pts.shape != (4, 2):
        raise ValueError("Cần đúng 4 điểm, mỗi điểm có dạng (x, y).")

    rect = np.zeros((4, 2), dtype=np.float32)

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()

    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left

    return rect

def compute_output_size(rect):
    tl, tr, br, bl = rect

    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    max_width = int(round(max(width_top, width_bottom)))

    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    max_height = int(round(max(height_left, height_right)))

    max_width = max(max_width, 1)
    max_height = max(max_height, 1)

    return max_width, max_height

INTERPOLATIONS = {
    "Nearest": cv2.INTER_NEAREST,
    "Linear": cv2.INTER_LINEAR,
    "Cubic": cv2.INTER_CUBIC,
    "Lanczos4": cv2.INTER_LANCZOS4
}

BORDER_MODES = {
    "Constant": cv2.BORDER_CONSTANT,
    "Replicate": cv2.BORDER_REPLICATE,
    "Reflect": cv2.BORDER_REFLECT
}

def perspective_transform(
    image,
    src_points,
    output_width=None,
    output_height=None,
    interpolation="Linear",
    border_mode="Constant",
    border_value=(255,255,255)
):
    if image is None:
        raise ValueError("Ảnh đầu vào đang là None.")

    rect = order_points(src_points)

    auto_w, auto_h = compute_output_size(rect)

    out_w = auto_w if output_width is None else int(output_width)
    out_h = auto_h if output_height is None else int(output_height)

    if out_w <= 0 or out_h <= 0:
        raise ValueError("Kích thước output phải > 0.")

    dst = np.array([
        [0, 0],
        [out_w - 1, 0],
        [out_w - 1, out_h - 1],
        [0, out_h - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(rect, dst)

    t0 = time.perf_counter()
    warped = cv2.warpPerspective(
        image,
        M,
        (out_w, out_h),
        flags=INTERPOLATIONS[interpolation],
        borderMode=BORDER_MODES[border_mode],
        borderValue=border_value
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return warped, M, rect, dst, elapsed_ms

def polygon_area(points):
    p = order_points(points)
    x = p[:,0]
    y = p[:,1]
    return 0.5 * abs(
        np.dot(x, np.roll(y, 1)) -
        np.dot(y, np.roll(x, 1))
    )

def laplacian_variance(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def reprojection_error(src_pts, dst_pts, H):
    src = order_points(src_pts).reshape(-1,1,2).astype(np.float32)
    projected = cv2.perspectiveTransform(src, H).reshape(-1,2)
    err = np.linalg.norm(projected - dst_pts, axis=1)
    return projected, err

def make_synthetic_document(width=700, height=500):
    doc = np.full((height, width, 3), 255, dtype=np.uint8)

    cv2.rectangle(doc, (20,20), (width-20,height-20), (0,0,0), 3)
    cv2.putText(doc, "PROJECT 2026 - DOCUMENT SCAN",
                (45,80), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0,0,0), 2)

    y = 140
    for i in range(7):
        cv2.line(doc, (60,y), (width-70,y), (80,80,80), 2)
        y += 45

    cv2.rectangle(doc, (470,310), (620,420), (120,120,120), 2)
    cv2.putText(doc, "IMG", (505,375),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80,80,80), 2)

    return doc

def mse(img1, img2):
    a = img1.astype(np.float32)
    b = img2.astype(np.float32)
    return float(np.mean((a-b)**2))

def psnr(img1, img2):
    m = mse(img1, img2)
    if m == 0:
        return float("inf")
    return 10.0 * np.log10((255.0**2)/m)

def ssim_global(img1, img2):
    # SSIM global đơn giản, không dùng thư viện ngoài.
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY).astype(np.float64)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY).astype(np.float64)

    mu1, mu2 = g1.mean(), g2.mean()
    var1, var2 = g1.var(), g2.var()
    cov12 = ((g1-mu1)*(g2-mu2)).mean()

    C1 = (0.01*255)**2
    C2 = (0.03*255)**2

    num = (2*mu1*mu2 + C1) * (2*cov12 + C2)
    den = (mu1**2 + mu2**2 + C1) * (var1 + var2 + C2)

    return float(num/den)

def scan_perspective(
    image,
    points,
    interpolation="Linear",
    border_mode="Constant",
    output_width=None,
    output_height=None
):
    result, M, src, dst, t = perspective_transform(
        image,
        points,
        output_width=output_width,
        output_height=output_height,
        interpolation=interpolation,
        border_mode=border_mode
    )

    info = {
        "matrix": M,
        "src_points": src,
        "dst_points": dst,
        "output_width": result.shape[1],
        "output_height": result.shape[0],
        "processing_time_ms": t,
        "sharpness": laplacian_variance(result)
    }

    return result, info
