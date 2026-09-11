# Hướng dẫn đọc và trình bày source

Nên đọc theo thứ tự sau:

1. `main.py`: tạo QApplication, mở cửa sổ và bắt đầu vòng lặp giao diện.
2. `scan_app/window.py`: `set_light_theme` đặt Fusion và màu sáng; các hàm `build_*` dựng từng phần giao diện.
3. Trong `window.py`, lần theo `apply_transform` → `parameters` → `TransformWorker.run` → `show_result`. Worker chỉ để xử lý ảnh mà không làm đứng cửa sổ.
4. `processing/resize.py`, `rotate.py`, `perspective.py`: mỗi file là một kỹ thuật. Hàm kiểm tra và metric dùng chung nằm trong `processing/__init__.py`.
5. `canvas.py`: `mapToScene` đổi vị trí chuột sang pixel ảnh gốc; danh sách `points` giữ tọa độ khi click/kéo. Không còn ô nhập X/Y trên giao diện.
6. `image_io.py`: đọc byte rồi giải mã ảnh, mã hóa ảnh rồi ghi byte để hỗ trợ đường dẫn tiếng Việt.

## Những chỗ nên giải thích khi demo

- Resize giữ tỷ lệ bằng cách lấy chiều vừa sửa làm chuẩn. Khi gọi API với cả Width/Height, ảnh được thu vừa hộp giới hạn.
- Rotate bật Keep Full sẽ mở rộng canvas và dịch tâm xoay, giúp không mất góc ảnh.
- Perspective gọi trực tiếp `perspective_transform`: sắp bốn điểm, đo cạnh để tính đầu ra, tạo ma trận bằng `getPerspectiveTransform`, rồi gọi `warpPerspective`. Hàm trả ảnh và thông tin ma trận/góc/thời gian; `reprojection_error` chỉ dùng cho đánh giá chi tiết. Không còn hàm bọc `scan_perspective`.
- Before luôn là ảnh vừa mở. After là kết quả của lần áp dụng gần nhất; Reset bỏ kết quả và điểm chọn.
- Chi tiết Perspective chỉ giữ sai số chiếu lại bốn góc; SSIM global của bộ mô phỏng nằm trong `processing/__init__.py`. Chi tiết đánh giá chỉ hiện chỉ số liên quan đến kết quả. Không có xuất JSON hay lịch sử ghép bước trong giao diện hiện tại.

Các kiểm tra điểm trùng, thẳng hàng, ma trận suy biến và giới hạn 24 megapixel được giữ để tránh lỗi thật khi thao tác. Không cần học thuộc mọi chi tiết kiểm thử để giải thích ba kỹ thuật.

`tests/test_algorithms.py` đối chiếu các phép biến đổi với hàm gốc trong `tests/reference/`. `tests/test_gui.py` kiểm tra thao tác giao diện, màu sáng, kéo điểm và mở/lưu ảnh. Nguồn notebook và ghi chú thay đổi nằm ở [THAY_DOI.md](THAY_DOI.md).
