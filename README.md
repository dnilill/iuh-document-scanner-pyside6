# Scan tài liệu · Chủ đề 4 · Project 2026

Ứng dụng PySide6 chuyển phần Resize, Rotate và Perspective Transform từ **hai notebook của nhóm** thành project desktop. Đã đọc đề PDF 14 trang và toàn bộ cell của hai notebook trước khi triển khai. Phạm vi lần chuyển này là **Project 1: Scan tài liệu, trang 7**. Project 2: Đếm sản phẩm là bài riêng; hai notebook không chứa thuật toán của phần đó.

**Dành cho người review:** xem [hướng dẫn đọc source](docs/REVIEW_GUIDE.md), [thuật toán](scan_app/processing/) và [nhật ký sửa lỗi](docs/THAY_DOI.md). Repo chứa bản trích hàm gốc để đối chiếu trong `tests/reference/`.

![Giao diện scan tài liệu](docs/gui-preview.png)

## Chạy ngay trên máy hiện tại

Mở PowerShell tại thư mục project:

```powershell
.\.venv\Scripts\python.exe main.py
```

Mở sẵn một ảnh demo:

```powershell
.\.venv\Scripts\python.exe main.py samples/synthetic/document_01.png
```

Môi trường `.venv` đã được cài và kiểm thử. Để cài lại trên máy khác có Python 3.11 trở lên:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`requirements-lock.txt` ghi phiên bản chính xác của môi trường đã kiểm thử (Python 3.13, Windows). Có thể cài từ file này để tái lập cả môi trường kiểm thử. Không cài đồng thời `opencv-python` và `opencv-python-headless` trong cùng môi trường.

## Sử dụng

1. **Mở ảnh**, hoặc **Mở video** rồi nhập số khung hình và chọn **Lấy khung hình**. Video được dùng làm nguồn ảnh tĩnh; ứng dụng chưa xử lý/xuất cả luồng video.
2. Chọn tab **Resize**, **Rotate** hoặc **Perspective**, đặt tham số và bấm **Áp dụng phép biến đổi**.
3. Với phối cảnh: kéo 4 nút trên ảnh, nhập X/Y, hoặc xóa và bấm 4 góc theo thứ tự bất kỳ. Số 1–4 là số điểm nhập; thuật toán tự sắp xếp góc. Tọa độ dùng pixel ảnh gốc, có xử lý tỷ lệ hiển thị. Kích thước 0/Tự động giữ cách tính từ độ dài cạnh trong notebook; có thể chỉ định cả W/H để giữ tỷ lệ tài liệu mong muốn.
4. So sánh hai vùng Before/After và thanh Tool | Input | Output | Time | Status. Bật **Chi tiết đánh giá** để xem chỉ số phù hợp với kết quả đang hiển thị; toàn bộ metric và ma trận vẫn có trong JSON. Tham số được xử lý khi bấm Áp dụng, không tự chạy mỗi lần chỉnh. Lưu luôn dùng **kết quả lần chạy gần nhất**.
5. **Dùng kết quả làm đầu vào tiếp** để ghép nhiều bước, ví dụ Phối cảnh → Rotate → Resize. **Về ảnh gốc** xóa chuỗi bước và khôi phục ảnh ban đầu.
6. **Lưu ảnh kết quả** hỗ trợ PNG/JPEG/BMP/TIFF; **Xuất đánh giá JSON** lưu nguồn ảnh, lịch sử các bước, tham số, ma trận và chỉ số kết quả hiện tại.

Phần Rotate có góc dương ngược chiều kim đồng hồ, scale, giữ toàn bộ canvas, nội suy, kiểu biên và nền trắng/đen. Resize có năm kiểu nội suy; Rotate/Phối cảnh có bốn kiểu giống notebook phối cảnh. Khi Resize khóa tỷ lệ, sửa Width sẽ cập nhật Height và ngược lại theo ảnh đầu vào hiện tại. GUI truyền chiều vừa sửa vào thuật toán để tránh làm tròn hai lần; API `resize_image` vẫn giữ quy ước hộp giới hạn khi truyền cả W/H. Mở ảnh, đổi khung hình, ghép bước hoặc Reset đều cập nhật W/H theo ảnh đầu vào mới.

## Tái sử dụng và sửa lỗi

Đọc `docs/THAY_DOI.md` để xem bảng nguồn hàm và từng lỗi. `docs/source_manifest.json` ghi SHA-256 của notebook đầu vào và vị trí cell (đếm từ 0). `tests/reference/` chứa bản trích nguyên văn các hàm gốc dùng để kiểm tra hồi quy. Hai notebook gốc và PDF không bị sửa.

```text
main.py                            Điểm chạy ứng dụng
scan_app/processing/resize.py       Resize và đánh giá hồi kích thước
scan_app/processing/rotate.py       Rotate, canvas keep-full
scan_app/processing/perspective.py  Perspective và đánh giá phối cảnh
scan_app/processing/__init__.py     Hằng số, validation và metric dùng chung
scan_app/window.py                 Tham số, thao tác, worker và đánh giá
scan_app/canvas.py                 Hiển thị ảnh và chọn/kéo góc
scan_app/image_io.py               Đọc/ghi đường dẫn Unicode
tests/reference/                   Hàm nguyên văn từ notebook
tests/                             Đối chiếu thuật toán và kiểm thử GUI
scripts/generate_demo.py           Tạo dữ liệu tài liệu mô phỏng
samples/synthetic/                 10 ảnh mô phỏng, ground truth, kết quả
docs/                              Nguồn thuật toán, thay đổi và kiểm thử
```

## Kiểm thử và tái tạo demo

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.generate_demo
```

Nếu môi trường được tạo bằng `uv` không có pip, dùng `uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt`.

Script demo tạo lại các file có tên cố định trong `samples/synthetic`. `manifest.json` lưu bốn góc riêng cho từng ảnh; `evaluation.csv` có 40 dòng cho 10 ảnh × 4 kiểu nội suy. Để thử ảnh đầu tiên, mở `document_01.png`, nhập bốn góc từ manifest và đặt W=700, H=500.

## Cách hiểu đánh giá và phạm vi bàn giao

- Resize: MSE, PSNR, SSIM theo cửa sổ trên ảnh xám, sau khi đưa ảnh đã resize về kích thước gốc bằng Linear, đúng quy trình notebook. Đây là đánh giá mất mát qua resize và hồi kích thước.
- Phối cảnh: diện tích tứ giác, tỷ lệ diện tích, tỷ lệ W/H, Laplacian, thời gian và sai số chiếu lại bốn góc. Sai số rất nhỏ chỉ xác nhận ma trận ánh xạ đúng các góc đã chọn, không chứng minh người dùng chọn đúng mép tài liệu.
- Ground truth mô phỏng: giữ MSE/PSNR và **SSIM global đơn giản** của notebook Perspective. SSIM này khác SSIM cửa sổ của Resize. Thời gian `processing_time_ms` là riêng warp như notebook; thời gian tổng trong GUI có thêm kiểm tra và dựng thông tin.
- Rotate: kích thước, góc, scale, thời gian và Laplacian; kiểm thử bảo toàn pixel ở góc vuông và bao phủ các góc khi mở canvas. Không tính PSNR trực tiếp giữa hai ảnh khác hệ tọa độ.
- Giới hạn ảnh vào/ra 24 megapixel nhằm tránh cấp phát quá lớn. Giới hạn được kiểm tra sau giải mã ảnh đầu vào. Bốn góc cần nằm trong ảnh và tạo tứ giác lồi; ảnh giấy cong cần thuật toán khác ngoài phạm vi notebook.

Đã bàn giao phần mềm, dữ liệu **mô phỏng**, kiểm thử và ghi chú kỹ thuật. Đề còn yêu cầu báo cáo và video demo 5–15 phút; ghi chú trong `docs/` là tài liệu kỹ thuật hỗ trợ, chưa phải báo cáo học phần hoàn chỉnh. Nhóm cần bổ sung ảnh tài liệu thực tế để đánh giá khả năng ứng dụng và tự quay video thuyết trình/demo. Không coi dữ liệu mô phỏng là bằng chứng đã thử trên ảnh chụp thực tế.
