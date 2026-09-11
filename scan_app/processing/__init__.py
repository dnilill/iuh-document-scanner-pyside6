"""Hằng số, kiểm tra đầu vào và phép đo dùng chung. Ảnh uint8 grayscale/BGR."""
import cv2
import numpy as np

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


def gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def laplacian_variance(image):
    return float(cv2.Laplacian(gray(image), cv2.CV_64F).var())


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
