# Kết quả kiểm thử

Môi trường chạy: Windows, Python 3.13; xem `requirements-lock.txt` để có phiên bản thư viện. Kết quả lần chạy ngày 10/09/2026: **73 kiểm thử đạt**.

Đã kiểm tra:

- Resize đối chiếu trực tiếp ảnh output với hàm notebook trên 5 nội suy × 4 cấu hình hợp lệ.
- Perspective đối chiếu output, ma trận, góc nguồn/đích với notebook trên 4 nội suy × 3 kiểu biên.
- Các sửa lỗi khóa tỷ lệ, canvas xoay, tâm pixel, sắp góc hình thoi, dữ liệu đầu vào bất hợp lệ, SSIM ảnh nhỏ và Unicode I/O.
- GUI bằng Qt Test: mở ảnh, chạy worker, ghép Resize → Rotate, lưu PNG, xuất JSON có lịch sử, khôi phục ảnh gốc, click 4 góc trên canvas rồi warp.
- Video AVI thử nghiệm có ba khung hình: mở bằng hộp thoại giả lập, chọn khung số 2, kiểm tra giá trị pixel đọc được và giải phóng VideoCapture.
- Xem ảnh chụp widget với ảnh tài liệu mô phỏng để kiểm tra tiếng Việt, bố cục, điểm nguồn và ảnh sau biến đổi. Phép thử tự động dùng Qt offscreen; font Segoe UI được nạp rõ ràng cho chế độ này. Chưa thử thủ công mọi codec video hoặc mọi mức DPI màn hình.

## Bộ mô phỏng

Dùng nguyên hàm `make_synthetic_document` của notebook Perspective. Tạo 10 tứ giác với nhiễu tọa độ có seed 2026; hai ảnh thêm blur, hai ảnh đổi độ sáng. Mỗi ảnh có bốn góc thật đã biết, ghi trong `data/synthetic/manifest.json`. Có 40 cấu hình phối cảnh được đo bằng cùng metric trong notebook.

Kết quả trung bình trên 10 ảnh (PSNR đo theo dB; thời gian chỉ warp, phụ thuộc máy và tải lúc chạy):

| Nội suy | PSNR trung bình | SSIM global trung bình | Warp trung bình (ms) |
|---|---:|---:|---:|
| Nearest | 23.1353 | 0.960291 | 1.676 |
| Linear | 23.7306 | 0.962704 | 2.212 |
| Cubic | 25.2804 | 0.972403 | 4.894 |
| Lanczos4 | 25.5114 | 0.972863 | 13.508 |

Sai số reprojection lớn nhất trên 40 cấu hình: **1.3501e-13 pixel**. Kết quả chi tiết ở `data/synthetic/evaluation.csv`. Mỗi ảnh còn được chạy resize scale 0.5 và rotate 30°, với kích thước output ghi trong bảng.

Trên bộ mô phỏng này, Cubic/Lanczos4 có chỉ số trung bình tốt hơn nhưng thời gian cao hơn. Không suy rộng thứ hạng này cho mọi tài liệu thực tế. Blur/độ sáng khiến sai khác với ground truth bao gồm cả nhiễu đầu vào lẫn mất mát nội suy; MSE/PSNR không tách được từng nguyên nhân. SSIM global không thay thế SSIM cửa sổ, và reprojection gần 0 không chứng minh bốn góc do người dùng chọn là đúng.

## Việc cần có thêm để nộp đủ học phần

Ứng dụng và bộ mô phỏng phục vụ kiểm tra thuật toán đã có. Cần bổ sung đánh giá trên ảnh chụp tài liệu thực tế (ánh sáng kém, góc nghiêng, nền phức tạp, ảnh mờ), báo cáo học phần hoàn chỉnh và video demo 5–15 phút theo đề. Bộ mô phỏng không được ghi thành bộ ảnh chụp thật. Project 2 Đếm sản phẩm không nằm trong phần chuyển hai notebook này.
