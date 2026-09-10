# Nguồn thuật toán và nhật ký sửa lỗi

Đề chính thức: `Project_2026.pdf`, trang 7, Chủ đề 4 / Project 1: Rotate, Resize, Perspective Transform; thay tham số; hiển thị trước/sau; đánh giá; mở ảnh/video; lưu kết quả. Các ví dụ trong notebook được xem là tài liệu nguồn, không tự động thực thi pip, upload Colab, download ảnh mạng hay chạy các cell giao diện.

## Bảng đối chiếu (cell tính từ 0)

| Nguồn | Cell | Hàm/khối được tái sử dụng | Nơi chuyển sang |
|---|---:|---|---|
| Phần_Resize_Rotate.ipynb | 10 | INTERPOLATIONS, resize_image | scan_app/processing/resize.py |
| Phần_Resize_Rotate.ipynb | 12 | rotate_image | scan_app/processing/rotate.py |
| Phần_Resize_Rotate.ipynb | 14 | evaluate_resize | scan_app/processing/resize.py |
| Phần_Resize_Rotate.ipynb | 16 | Tham số, chạy, so sánh, lưu | scan_app/window.py (thay ipywidgets bằng Qt) |
| Phần_Resize_Rotate.ipynb | 19–20 | Chạy resize/rotate trên nhiều ảnh | scripts/generate_demo.py |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 7, 9, 11 | order_points, compute_output_size, perspective_transform | scan_app/processing/perspective.py (metric chung ở __init__.py) |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 13 | Vẽ polygon và điểm | scan_app/canvas.py (overlay Qt để kéo điểm) |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 21, 24 | polygon_area, laplacian_variance, reprojection_error | scan_app/processing/perspective.py (metric chung ở __init__.py) |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 26 | make_synthetic_document | tests/reference/perspective.py, được gọi từ script demo |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 27 | mse, psnr, ssim_global | scan_app/processing/perspective.py (metric chung ở __init__.py) |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 30, 34 | So sánh nội suy và batch | scripts/generate_demo.py; dùng bốn góc riêng mỗi ảnh |
| Perspective_Transform_Project2026_ChuDe4.ipynb | 36, 38 | UI tham số và scan_perspective | scan_app/window.py, scan_app/processing/perspective.py (metric chung ở __init__.py) |

Giữ nguyên các bước tính chính: `cv2.resize`; `getRotationMatrix2D` + dịch tâm + `warpAffine`; sắp xếp góc + đo cạnh + `getPerspectiveTransform` + `warpPerspective`. Không thêm phát hiện góc tự động, segmentation hoặc implementation warp khác.

## Lỗi đã sửa trong module chuyển đổi

| Vấn đề ở notebook | Cách sửa và thay đổi hành vi | Kiểm tra |
|---|---|---|
| Resize bật keep_aspect_ratio nhưng truyền cả width/height vẫn lấy nguyên cả hai, làm méo ảnh | Khi có cả hai, lấy min(W/w, H/h) để vừa trong hộp. Ví dụ ảnh 90×60 vào hộp 80×80 cho 80×53 thay vì 80×80. Trường hợp một chiều/scale vẫn dùng int như bản gốc. | test_resize_aspect_bug; đối chiếu 20 cấu hình resize |
| Thiếu kích thước làm max(1, None) lỗi; width float có thể gây lỗi OpenCV; scale âm/0 bị âm thầm ép 1 px | Kiểm tra số nguyên, hữu hạn, dương; trả ValueError rõ ràng. Scale dương rất nhỏ vẫn được chặn tối thiểu 1 px theo notebook. | test_invalid_resize |
| Xoay keep_full làm tròn xuống kích thước canvas nên cắt mép; tâm w/2,h/2 lệch tâm pixel gây mất hàng/cột ở góc 90/180/270 | Dùng ceil (trừ epsilon cho nhiễu số tại góc vuông); tâm (w−1)/2,(h−1)/2 và tâm canvas tương ứng. Giữ cùng ma trận xoay/warpAffine. Kết quả xoay khác bản gốc có chủ đích, kể cả góc không vuông. | 12 ca np.rot90 đối chiếu pixel; kiểm tra góc biên với 17° |
| order_points dùng sum/diff có thể chọn trùng một điểm, như hình thoi | Giữ sum/diff nếu trả 4 góc khác nhau hợp lệ. Chỉ fallback sắp vòng quanh tâm khi cách cũ thất bại; xác định điểm bắt đầu ổn định. Với hình đối xứng, tên TL có tính quy ước; dùng Rotate nếu cần đổi hướng đọc. | Hình thoi và cả 24 hoán vị; đối chiếu phối cảnh thông thường |
| Điểm trùng, lõm, thẳng hàng/gần thẳng hàng, NaN không bị chặn; ma trận có thể suy biến | Kiểm tra convex hull đủ 4 đỉnh, diện tích ≥1 px², độ cao tam giác cục bộ ≥0.5 px, tính hữu hạn và hạng ma trận; giới hạn điểm trong ảnh. | test_invalid_corners và kiểm tra điểm ngoài ảnh |
| Cho output phối cảnh W/H=1, dẫn đến đích co thành đường/điểm | Yêu cầu W/H ≥2, tính tự động chặn tối thiểu 2. Giữ quy ước chiều dài cạnh notebook (không cộng thêm 1), vì vậy chọn toàn ảnh để Tự động có thể nhỏ hơn đầu vào 1 px. Muốn identity phải nhập W/H gốc. | Identity, reprojection và từ chối chiều 1 |
| SSIM mặc định cần cửa sổ 7×7, lỗi trên ảnh nhỏ | Dùng cửa sổ lẻ ≤ min(7,H,W). Ảnh có cạnh <3 trả None, GUI ghi không áp dụng, không bịa giá trị. Ảnh ≥7 giữ phép đo cũ. | 6 kích thước nhỏ và đối chiếu metric gốc |
| cv2.imread/imwrite trực tiếp với đường dẫn tiếng Việt trên Windows dễ thất bại tùy bản build; lưu không kiểm tra kết quả | Dùng đọc byte + imdecode, imencode + ghi byte; kiểm tra ảnh, suffix và lỗi ghi. | Round trip PNG đường dẫn tiếng Việt |

## Refactor tích hợp, không phải thay thuật toán

- Tách thư viện GUI khỏi thuật toán; thay Colab/files/ipywidgets/matplotlib display bằng Qt. Không tự động chạy notebook đầu vào.
- Giữ tên và giá trị các nội suy. Tách map Resize (có Area) khỏi map phối cảnh (không Area), tránh hai notebook ghi đè cùng tên `INTERPOLATIONS` khi ghép.
- Rotate bổ sung lựa chọn nội suy và biên; mặc định vẫn Linear, Constant, nền trắng.
- `scan_perspective` giữ toàn bộ khóa thông tin gốc, bổ sung diện tích và reprojection. Tuple `perspective_transform` giữ nguyên.
- `evaluate_resize` đổi nhãn `SSIM` thành `SSIM (cửa sổ)` trong ứng dụng để phân biệt với `ssim_global`. PSNR dùng công thức có sẵn trong notebook Perspective; đối chiếu khớp số làm tròn với skimage của notebook Resize.
- QThread chạy phép biến đổi và tính metric để GUI tiếp tục phản hồi. Khóa thay đổi nguồn trong khi chạy; nếu chạy lỗi thì bỏ kết quả cũ để tránh lưu nhầm.
- Bốn góc dùng tọa độ ảnh qua phép ánh xạ QGraphicsView, không dùng tọa độ màn hình làm đầu vào warp. Overlay polygon sắp góc để hiển thị đúng cả khi người dùng chọn không theo vòng.
- Chọn khung hình video, ghép kết quả nhiều bước, xuất JSON kèm lịch sử là phần tích hợp mới.
- Không chuyển chức năng tự tải ảnh Picsum và tự augment cho đủ số lượng. Phần augment gốc có nguy cơ lặp vô hạn nếu mọi file mang đuôi ảnh đều hỏng; luồng này được bỏ khỏi ứng dụng, không tuyên bố đã sửa notebook gốc. Script demo dùng hàm tài liệu mô phỏng có sẵn và vòng lặp hữu hạn, hạt giống cố định.

## Xác minh nguồn

`source_manifest.json` lưu SHA-256 và cell cho từng hàm. Các file trong `tests/reference/` chỉ trích khai báo hàm và hằng số, không chạy các cell tải dữ liệu/UI. Chúng là baseline bất biến cho kiểm thử; không được dùng làm phiên bản production chưa kiểm tra đầu vào.

## Refactor source và UI ngày 10/09/2026

- Tách `algorithms.py` thành `processing/resize.py`, `rotate.py`, `perspective.py`; hằng số, validation và metric dùng chung ở `processing/__init__.py`. Giữ nguyên thân tất cả hàm thuật toán, không thêm tầng service/controller. Cập nhật import trong GUI, canvas, I/O, test và script demo.
- Chuyển dữ liệu mô phỏng từ `data/synthetic/` sang `samples/synthetic/`; giữ nguyên ảnh, manifest và số liệu đã có.
- Giữ tab Resize/Rotate/Perspective, chỉ hiện tham số đúng chế độ; tăng vùng Before/After, cân bằng hai canvas. Thanh tóm tắt luôn mô tả kết quả đang hiển thị, kể cả khi chuyển tab. Metric chi tiết mặc định thu gọn, chỉ hiển thị ba thông số phù hợp; JSON vẫn đầy đủ.
- Resize đồng bộ hai chiều theo tỷ lệ ảnh hiện tại, chặn signal lặp khi cập nhật ô; chỉ truyền chiều vừa chỉnh vào thuật toán khi khóa tỷ lệ để tránh làm tròn hai lần. Không thay API hộp giới hạn của thuật toán.
- Perspective giữ polygon, click/drag và nhập tọa độ; báo ngay số điểm còn thiếu hoặc tứ giác không hợp lệ. Worker vẫn bắt lỗi và vô hiệu hóa lưu kết quả cũ sau khi xử lý lỗi.
- Giữ Open Image/Video, Save Result, Reset, ghép bước và xuất JSON; giữ BGR/RGB và I/O Unicode.
- Lần refactor này không tìm thấy PDF gốc trong workspace/thư mục IUH; đối chiếu theo yêu cầu người dùng và phần đề đã ghi lại ở đầu tài liệu này.

### Danh sách file thay đổi trong lần refactor

- Thay `scan_app/algorithms.py` bằng `scan_app/processing/__init__.py`, `scan_app/processing/resize.py`, `scan_app/processing/rotate.py`, `scan_app/processing/perspective.py`.
- Sửa `scan_app/window.py`; cập nhật import trong `scan_app/canvas.py`, `scan_app/image_io.py`.
- Cập nhật `tests/test_algorithms.py`, `tests/test_gui.py`, `scripts/generate_demo.py`.
- Cập nhật `README.md`, `docs/REVIEW_GUIDE.md`, `docs/THAY_DOI.md`, `docs/KIEM_THU.md`, `docs/gui-preview.png`.
- Chuyển nguyên 23 file từ `data/synthetic/` sang `samples/synthetic/`: `document_01.png`–`document_10.png`, `restored_01.png`–`restored_10.png`, `ground_truth.png`, `manifest.json`, `evaluation.csv`.
- `main.py`, requirements và các hàm baseline trong `tests/reference/` không cần sửa.
