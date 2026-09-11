# Kết quả kiểm thử

## Sau khi đơn giản hóa Perspective – 11/09/2026

**84 test đạt** với `python -X utf8 -m pytest -q`.

- Giữ 82 test trước đó; cập nhật cách gọi từ `scan_perspective` sang `perspective_transform` và import SSIM, giữ các điều kiện kiểm tra cũ.
- Thêm test 24 thứ tự click cho tứ giác và tính kích thước tự động, test thiếu ảnh/điểm/kích thước đầu ra sai. Test GUI bổ sung lưu và mở lại kết quả Perspective với tên file tiếng Việt.
- Smoke test trực tiếp Qt/Windows: mở `document_01.png`, click bốn góc theo thứ tự 3–1–4–2, đổi kích thước cửa sổ rồi kéo góc, Apply ra ảnh 700×500, Save PNG tên tiếng Việt và đối chiếu toàn bộ pixel khi mở lại. Polygon và bốn control point vẫn có; sai số chiếu lại < 0.001 px.
- Đã chụp và xem GUI mới tại `docs/gui-preview.png`. Resize/Rotate/canvas không thay đổi trong lần này.

## Phiên bản trước khi rút gọn Perspective – 11/09/2026

**82 test đạt** với `python -X utf8 -m pytest -q` trên Windows, Python 3.13.

- Giữ toàn bộ các hàm test, gồm đối chiếu thuật toán Resize/Rotate/Perspective, giữ tỷ lệ, không crop khi xoay, ánh xạ bốn góc, Unicode, mở/lưu và GUI.
- Bỏ assertion liên quan đến xuất JSON, lịch sử ghép bước và ô X/Y vì đã bỏ các chức năng này. Workflow hiện áp dụng từng phép biến đổi lên ảnh Before. Không bỏ test để che lỗi thuật toán.
- Thêm test khởi tạo từ palette tối để kiểm tra palette sáng, và test mở ảnh lỗi không làm mất nguồn ảnh hiện tại. Qt offscreen không cung cấp color scheme của hệ điều hành, nên test offscreen kiểm tra màu thực tế của palette/widget.
- Đã chạy cả ba kỹ thuật bằng Qt platform `windows` trong khi Windows đang đặt Dark Mode (`AppsUseLightTheme=0`, `SystemUsesLightTheme=0`). App báo color scheme Light, các panel giữ nền sáng; không thay đổi cài đặt Windows.
- Đã xem ảnh chụp ba tab, màn hình chi tiết tại 1100×750 và màn hình chính tại 1280×800. Screenshot mới: `docs/gui-preview.png`.
- Đã chạy entry point với cửa sổ trống và với ảnh mẫu; cả hai mở/đóng thành công trên Qt/Windows.

## Các lần kiểm tra trước (10/09/2026)

Môi trường chạy: Windows, Python 3.13; xem `requirements-lock.txt` để có phiên bản thư viện. Kết quả lần chạy ngày 10/09/2026: **80 kiểm thử đạt** (73 test cũ được giữ nguyên phạm vi; thêm 7 trường hợp GUI).

Đã kiểm tra:

- Resize đối chiếu trực tiếp ảnh output với hàm notebook trên 5 nội suy × 4 cấu hình hợp lệ.
- Perspective đối chiếu output, ma trận, góc nguồn/đích với notebook trên 4 nội suy × 3 kiểu biên.
- Các sửa lỗi khóa tỷ lệ, canvas xoay, tâm pixel, sắp góc hình thoi, dữ liệu đầu vào bất hợp lệ, SSIM ảnh nhỏ và Unicode I/O.
- GUI bằng Qt Test: mở ảnh, chạy worker, ghép Resize → Rotate, lưu PNG, xuất JSON có lịch sử, khôi phục ảnh gốc, click 4 góc trên canvas rồi warp.
- Video AVI thử nghiệm có ba khung hình: mở bằng hộp thoại giả lập, chọn khung số 2, kiểm tra giá trị pixel đọc được và giải phóng VideoCapture.
- Xem ảnh chụp widget với ảnh tài liệu mô phỏng để kiểm tra tiếng Việt, bố cục, điểm nguồn và ảnh sau biến đổi. Phép thử tự động dùng Qt offscreen; font Segoe UI được nạp rõ ràng cho chế độ này. Chưa thử thủ công mọi codec video hoặc mọi mức DPI màn hình.

## Bổ sung sau refactor source/UI

- Resize đồng bộ Width/Height cả hai chiều, làm tròn pixel khớp output, bật/tắt giữ tỷ lệ, mở ảnh kích thước khác.
- Ẩn tham số không thuộc tab/chế độ hiện tại; thu gọn/mở đánh giá, metric theo phép biến đổi, thanh trạng thái vẫn mô tả đúng ảnh After khi đổi tab.
- Chưa mở ảnh gọi Apply/Save/Reset; Reset sau xử lý; Perspective thiếu 4 điểm hoặc trùng điểm báo lỗi và có thể chọn lại để chạy tiếp.
- Kéo điểm bằng Qt Test sau đổi kích thước cửa sổ, đối chiếu tọa độ spinbox và polygon; kiểm tra màu BGR thành RGB trong pixmap; đổi tên video kiểm thử sang đường dẫn tiếng Việt.

- Entry point `main.main()` khởi động thành công bằng Qt platform `windows`, cả khi chưa mở ảnh và khi truyền ảnh demo qua tham số dòng lệnh; đóng sạch bằng Qt event loop.
- Đối chiếu AST: cả 17 hàm xử lý giữ nguyên so với commit trước refactor. Toàn bộ 23 file dữ liệu có Git blob hash không đổi sau khi chuyển sang `samples/synthetic/`.
- Đã xem ảnh chụp GUI ở 1280×800 và 1100×750; tab Resize gọn theo nội dung, hai canvas cân đối, không tràn ngang vùng tham số.

## Bộ mô phỏng

Dùng nguyên hàm `make_synthetic_document` của notebook Perspective. Tạo 10 tứ giác với nhiễu tọa độ có seed 2026; hai ảnh thêm blur, hai ảnh đổi độ sáng. Mỗi ảnh có bốn góc thật đã biết, ghi trong `samples/synthetic/manifest.json`. Có 40 cấu hình phối cảnh được đo bằng cùng metric trong notebook.

Kết quả trung bình trên 10 ảnh (PSNR đo theo dB; thời gian chỉ warp, phụ thuộc máy và tải lúc chạy):

| Nội suy | PSNR trung bình | SSIM global trung bình | Warp trung bình (ms) |
|---|---:|---:|---:|
| Nearest | 23.1353 | 0.960291 | 1.676 |
| Linear | 23.7306 | 0.962704 | 2.212 |
| Cubic | 25.2804 | 0.972403 | 4.894 |
| Lanczos4 | 25.5114 | 0.972863 | 13.508 |

Sai số reprojection lớn nhất trên 40 cấu hình: **1.3501e-13 pixel**. Kết quả chi tiết ở `samples/synthetic/evaluation.csv`. Mỗi ảnh còn được chạy resize scale 0.5 và rotate 30°, với kích thước output ghi trong bảng.

Trên bộ mô phỏng này, Cubic/Lanczos4 có chỉ số trung bình tốt hơn nhưng thời gian cao hơn. Không suy rộng thứ hạng này cho mọi tài liệu thực tế. Blur/độ sáng khiến sai khác với ground truth bao gồm cả nhiễu đầu vào lẫn mất mát nội suy; MSE/PSNR không tách được từng nguyên nhân. SSIM global không thay thế SSIM cửa sổ, và reprojection gần 0 không chứng minh bốn góc do người dùng chọn là đúng.

## Việc cần có thêm để nộp đủ học phần

Ứng dụng và bộ mô phỏng phục vụ kiểm tra thuật toán đã có. Cần bổ sung đánh giá trên ảnh chụp tài liệu thực tế (ánh sáng kém, góc nghiêng, nền phức tạp, ảnh mờ), báo cáo học phần hoàn chỉnh và video demo 5–15 phút theo đề. Bộ mô phỏng không được ghi thành bộ ảnh chụp thật. Project 2 Đếm sản phẩm không nằm trong phần chuyển hai notebook này.
