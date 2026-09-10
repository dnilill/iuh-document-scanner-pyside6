# Hướng dẫn review source code

Ứng dụng desktop PySide6 cho Chủ đề 4 / Project 1: Scan tài liệu. Repository public phục vụ đọc, chạy và kiểm tra source; đây không phải ứng dụng web chạy trên GitHub Pages.

## Thứ tự đọc

1. [README](../README.md): phạm vi, cách chạy, tính năng và giới hạn.
2. [Nguồn và sửa lỗi](THAY_DOI.md): bảng ánh xạ cell notebook sang module, giải thích từng thay đổi.
3. [Thuật toán production](../scan_app/algorithms.py): resize, rotate, perspective và metric.
4. Baseline trích nguyên văn: [Resize/Rotate](../tests/reference/resize_rotate.py), [Perspective](../tests/reference/perspective.py). [Manifest](source_manifest.json) lưu hash notebook và vị trí cell.
5. [GUI](../scan_app/window.py), [canvas chọn góc](../scan_app/canvas.py), [I/O Unicode](../scan_app/image_io.py), [entry point](../main.py).
6. [Kiểm thử thuật toán](../tests/test_algorithms.py), [kiểm thử GUI](../tests/test_gui.py), [kết quả kiểm thử](KIEM_THU.md).
7. [Script dữ liệu mô phỏng](../scripts/generate_demo.py), [góc ground truth](../data/synthetic/manifest.json), [kết quả định lượng](../data/synthetic/evaluation.csv).

PDF đề bài và notebook đầy đủ không nằm trong repo; có phần yêu cầu liên quan được ghi lại và các hàm baseline đã trích. Người review cần các file gốc nếu muốn xác minh độc lập nội dung đề và SHA-256, hoặc đọc các cell khác ngoài phần thuật toán đã trích.

## Các điểm cần đánh giá

- Mức độ giữ đúng thuật toán notebook và tính cần thiết của các thay đổi đã mô tả.
- Quy ước tọa độ pixel, giữ tỷ lệ, mở canvas xoay, thứ tự góc, tứ giác suy biến và ảnh rất nhỏ.
- SSIM cửa sổ của Resize so với SSIM global của Perspective; ý nghĩa và giới hạn của reprojection, Laplacian, PSNR.
- Chọn/kéo góc khi đổi kích thước cửa sổ; vòng đời QThread; ghép bước và tránh lưu nhầm kết quả.
- Xử lý lỗi khi đọc ảnh/video, kích thước lớn, Unicode và xuất JSON.
- Chất lượng và phần còn thiếu trong các kiểm thử. 73 kiểm thử đạt là kết quả đã ghi nhận, không bảo đảm code không còn bug.

## Prompt có thể gửi kèm link repo

> Hãy review repository này. Đọc README.md, docs/REVIEW_GUIDE.md và docs/THAY_DOI.md trước, sau đó đọc toàn bộ scan_app/ và tests/. Đối chiếu thuật toán production với hàm gốc trong tests/reference/. Tìm lỗi có thể tái hiện, phân loại mức độ, chỉ rõ file/dòng và cách sửa tối thiểu. Không tự thay thuật toán của nhóm bằng implementation khác nếu chưa chứng minh cần thiết. Kiểm tra cả GUI, metric và các trường hợp biên. Phân biệt kết quả kiểm thử đã có với nhận định chưa được chạy xác minh. Nếu không truy cập được một file, hãy nói rõ file nào thay vì suy đoán nội dung.
