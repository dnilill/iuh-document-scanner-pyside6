"""10 ảnh mô phỏng từ make_synthetic_document của notebook; không tải ảnh mạng.
Chạy tại thư mục project: python -m scripts.generate_demo
"""
import csv
import json
from pathlib import Path
import cv2
import numpy as np
from scan_app import algorithms as alg
from scan_app.image_io import write_image
from tests.reference.perspective import make_synthetic_document


def main():
    output = Path('data/synthetic')
    output.mkdir(parents=True, exist_ok=True)
    doc = make_synthetic_document()
    write_image(output/'ground_truth.png', doc)
    src = np.float32([[0, 0], [699, 0], [699, 499], [0, 499]])
    rng = np.random.default_rng(2026)
    manifest, rows = [], []
    for i in range(10):
        points = np.float32([[120, 80], [760, 40], [820, 610], [80, 650]])
        points += rng.integers(-25, 26, points.shape).astype(np.float32)
        H = cv2.getPerspectiveTransform(src, points)
        image = cv2.warpPerspective(doc, H, (900, 700), borderValue=(220, 220, 220))
        if i in (3, 7):
            image = cv2.GaussianBlur(image, (3, 3), .8)
        if i in (4, 8):
            image = cv2.convertScaleAbs(image, alpha=.8, beta=10)
        name = f'document_{i+1:02d}.png'
        write_image(output/name, image)
        manifest.append({'image': name, 'points': points.tolist(), 'output_width': 700,
                         'output_height': 500, 'type': 'synthetic',
                         'blur': i in (3, 7), 'brightness_changed': i in (4, 8)})
        for interpolation in alg.PERSPECTIVE_INTERPOLATIONS:
            restored, info = alg.scan_perspective(image, points, interpolation=interpolation,
                                                 output_width=700, output_height=500)
            resized = alg.resize_image(image, scale=.5)
            rotated = alg.rotate_image(image, angle=30)
            rows.append({'image': name, 'interpolation': interpolation,
                'MSE': alg.mse(doc, restored), 'PSNR_dB': alg.psnr(doc, restored),
                'SSIM_global': alg.ssim_global(doc, restored),
                'reprojection_max_px': info['reprojection_max_px'],
                'warp_ms': info['processing_time_ms'],
                'resize_shape': str(resized.shape), 'rotate_shape': str(rotated.shape)})
            if interpolation == 'Linear':
                write_image(output/f'restored_{i+1:02d}.png', restored)
    (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output/'evaluation.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Đã tạo 10 ảnh mô phỏng, ground truth, 10 ảnh hiệu chỉnh và {len(rows)} dòng đánh giá: {output}')


if __name__ == '__main__':
    main()
