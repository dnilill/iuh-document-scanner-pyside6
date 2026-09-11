"""PySide6 GUI. Worker xử lý ảnh không chặn vòng lặp giao diện."""
import time
from pathlib import Path
import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QSignalBlocker
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QTabWidget, QFormLayout, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QGroupBox,
)
from .processing import (
    validate_image, INTERPOLATIONS, PERSPECTIVE_INTERPOLATIONS,
)
from .processing.resize import resize_image, evaluate_resize
from .processing.rotate import rotate_image
from .processing.perspective import order_points, scan_perspective
from .canvas import ImageCanvas
from .image_io import read_image, write_image


def spin(value, minimum, maximum, decimals=False):
    widget = QDoubleSpinBox() if decimals else QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    if decimals:
        widget.setDecimals(3)
        widget.setSingleStep(0.05)
    return widget


def combo(items):
    widget = QComboBox()
    widget.addItems(list(items))
    if 'Linear' in items:
        widget.setCurrentText('Linear')
    return widget


def set_light_theme():
    """Cố định màu sáng, kể cả khi Windows dùng Dark Mode."""
    app = QApplication.instance()
    app.setStyle('Fusion')
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: '#f5f7fa',
        QPalette.ColorRole.WindowText: '#243749',
        QPalette.ColorRole.Base: '#ffffff',
        QPalette.ColorRole.AlternateBase: '#edf2f5',
        QPalette.ColorRole.Text: '#243749',
        QPalette.ColorRole.Button: '#ffffff',
        QPalette.ColorRole.ButtonText: '#243749',
        QPalette.ColorRole.Highlight: '#007d6b',
        QPalette.ColorRole.HighlightedText: '#ffffff',
        QPalette.ColorRole.ToolTipBase: '#ffffff',
        QPalette.ColorRole.ToolTipText: '#243749',
        QPalette.ColorRole.PlaceholderText: '#657585',
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor('#75808b'))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, QColor('#edf0f3'))
    app.setPalette(palette)


class TransformWorker(QThread):
    result_ready = Signal(object, object)
    failed = Signal(str)

    def __init__(self, image, operation, params):
        super().__init__()
        self.image, self.operation, self.params = image.copy(), operation, params

    def run(self):
        try:
            start = time.perf_counter()
            if self.operation == 'Resize':
                result = resize_image(self.image, **self.params)
                elapsed = (time.perf_counter()-start)*1000
                info = evaluate_resize(self.image, result)
                info['Ghi chú'] = 'Resize rồi hồi kích thước bằng Linear; không phải ground-truth độc lập.'
            elif self.operation == 'Rotate':
                result = rotate_image(self.image, **self.params)
                elapsed = (time.perf_counter()-start)*1000
                info = {'Góc (độ, dương = ngược kim đồng hồ)': self.params['angle'],
                        'Scale xoay': self.params['scale'], 'Giữ toàn bộ': self.params['keep_full']}
            else:
                result, info = scan_perspective(self.image, **self.params)
                elapsed = (time.perf_counter()-start)*1000
                info['Ghi chú'] = 'Reprojection kiểm tra ánh xạ 4 góc; không đánh giá độ đúng khi chọn góc.'
            info.update({'Phép biến đổi': self.operation,
                         'Đầu vào (W×H)': f'{self.image.shape[1]}×{self.image.shape[0]}',
                         'Đầu ra (W×H)': f'{result.shape[1]}×{result.shape[0]}',
                         'Thời gian biến đổi và kiểm tra (ms)': elapsed})
            self.result_ready.emit(result, info)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        set_light_theme()
        self.setWindowTitle('Scan tài liệu • Chủ đề 4 | Project 2026')
        self.resize(1280, 800)
        self.current = self.result = None
        self.worker = None
        self.info = {}
        self.source = ''
        self.result_status = 'Mở ảnh để bắt đầu'
        self.video = None
        self.video_path = None
        self.setStyleSheet('''
            QMainWindow, QWidget { font-family: "Segoe UI"; font-size: 13px; color: #243749; }
            QWidget { background: #f5f7fa; }
            QTabWidget::pane { background: #f5f7fa; border: 1px solid #c7d2de; }
            QTabBar::tab { background: #e9eef3; padding: 8px 10px; }
            QTabBar::tab:selected { background: #ffffff; color: #006b5b; }
            QComboBox, QSpinBox, QDoubleSpinBox { background: #ffffff; }
            QComboBox QAbstractItemView { background: #ffffff; color: #243749; selection-background-color: #007d6b; selection-color: white; }
            QPushButton { background: #ffffff; border: 1px solid #c7d2de; border-radius: 5px; padding: 8px 12px; }
            QPushButton:hover { background: #e4f4ef; }
            QPushButton:disabled { color: #75808b; background: #edf0f3; }
            QPushButton#primary { background: #007d6b; color: white; font-weight: 600; }
            QPushButton#primary:disabled, QComboBox:disabled, QSpinBox:disabled,
            QDoubleSpinBox:disabled { background: #edf0f3; color: #75808b; }
            QGroupBox { font-weight: 600; border: 1px solid #d7e0e8; border-radius: 6px; margin-top: 12px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QSpinBox, QDoubleSpinBox, QComboBox { min-height: 27px; }
            QTableWidget { background: white; gridline-color: #e1e7ed; }
        ''')
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        heading = QLabel('SCAN TÀI LIỆU')
        heading.setStyleSheet('font-size: 24px; font-weight: 700; color: #006b5b;')
        layout.addWidget(heading)
        self.build_toolbar(layout)
        split = QSplitter()
        layout.addWidget(split, 1)
        self.build_controls(split)
        self.build_preview(split)
        self.tabs.currentChanged.connect(self.mode_changed)
        self.before.points_changed.connect(self.sync_points)
        self.statusBar().showMessage('Sẵn sàng · Mở ảnh hoặc chọn một khung hình video')
        self.set_busy(False)
        self.mode_changed()
        self.update_summary('Mở ảnh để bắt đầu')

    def build_toolbar(self, layout):
        toolbar = QHBoxLayout()
        self.open_button = self.button('Mở ảnh', self.open_image, toolbar)
        self.video_button = self.button('Mở video', self.open_video, toolbar)
        self.reset_button = self.button('Về ảnh gốc', self.reset_image, toolbar)
        toolbar.addStretch()
        self.save_button = self.button('Lưu ảnh kết quả', self.save_image, toolbar)
        layout.addLayout(toolbar)
        self.video_bar = QWidget()
        row = QHBoxLayout(self.video_bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel('Video · Khung hình số (từ 0):'))
        self.frame_index = spin(0, 0, 0)
        row.addWidget(self.frame_index)
        self.button('Lấy khung hình', self.read_frame, row)
        row.addWidget(QLabel('Chọn một khung hình để scan và lưu thành ảnh.'))
        row.addStretch()
        self.video_bar.hide()
        layout.addWidget(self.video_bar)

    def build_controls(self, split):
        self.controls = QWidget()
        controls_layout = QVBoxLayout(self.controls)
        self.tabs = QTabWidget()
        controls_layout.addWidget(self.tabs)
        self.build_resize()
        self.build_rotate()
        self.build_perspective()
        self.apply_button = self.button('Áp dụng phép biến đổi', self.apply_transform, controls_layout)
        self.apply_button.setObjectName('primary')
        hint = QLabel('Mỗi lần áp dụng đều dùng ảnh Before.')
        hint.setWordWrap(True)
        controls_layout.addWidget(hint)
        controls_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.controls)
        scroll.setMinimumWidth(350)
        split.addWidget(scroll)

    def build_preview(self, split):
        right = QWidget()
        right_layout = QVBoxLayout(right)
        images = QSplitter()
        images.setChildrenCollapsible(False)
        self.before = ImageCanvas()
        self.after = ImageCanvas()
        for title, canvas in [('BEFORE · Ảnh đầu vào', self.before), ('AFTER · Kết quả', self.after)]:
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(canvas)
            images.addWidget(box)
        images.setSizes([450, 450])
        right_layout.addWidget(images, 1)
        self.point_status = QLabel('Mở ảnh để bắt đầu. Có thể kéo đường chia để mở rộng vùng xem.')
        self.point_status.setWordWrap(True)
        right_layout.addWidget(self.point_status)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet('background: #e4f4ef; padding: 10px; border-radius: 5px;')
        right_layout.addWidget(self.summary)
        self.details_toggle = QCheckBox('Chi tiết đánh giá')
        right_layout.addWidget(self.details_toggle)
        self.evaluation_note = QLabel()
        self.evaluation_note.setWordWrap(True)
        right_layout.addWidget(self.evaluation_note)
        self.metrics = QTableWidget(0, 2)
        self.metrics.setHorizontalHeaderLabels(['Thông số', 'Giá trị'])
        self.metrics.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.metrics.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.metrics.verticalHeader().hide()
        self.metrics.setFixedHeight(130)
        right_layout.addWidget(self.metrics)
        self.details_toggle.toggled.connect(self.update_details)
        self.update_details()
        split.addWidget(right)
        split.setSizes([350, 930])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setChildrenCollapsible(False)

    def button(self, text, callback, layout):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def tab_form(self, title):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.tabs.addTab(widget, title)
        return form

    def build_resize(self):
        form = self.tab_form('Resize')
        self.resize_form = form
        self.resize_axis = 'width'
        self.resize_target = 800
        self.resize_mode = combo(['Theo scale', 'Theo kích thước'])
        self.resize_scale = spin(1, .01, 10, True)
        self.resize_width = spin(800, 1, 24_000_000)
        self.resize_height = spin(600, 1, 24_000_000)
        self.keep_ratio = QCheckBox('Keep Aspect Ratio · Giữ tỷ lệ')
        self.keep_ratio.setChecked(True)
        self.resize_interp = combo(INTERPOLATIONS)
        for name, widget in [('Chế độ', self.resize_mode), ('Scale', self.resize_scale),
                ('Rộng (px)', self.resize_width), ('Cao (px)', self.resize_height),
                ('', self.keep_ratio), ('Nội suy', self.resize_interp)]:
            form.addRow(name, widget)
        self.resize_mode.currentIndexChanged.connect(self.resize_mode_changed)
        self.resize_width.valueChanged.connect(lambda: self.sync_resize_size('width'))
        self.resize_height.valueChanged.connect(lambda: self.sync_resize_size('height'))
        self.keep_ratio.toggled.connect(lambda: self.sync_resize_size(self.resize_axis))
        self.resize_mode_changed()

    def resize_mode_changed(self):
        scaled = self.resize_mode.currentIndex() == 0
        self.resize_form.setRowVisible(self.resize_scale, scaled)
        for widget in (self.resize_width, self.resize_height, self.keep_ratio):
            self.resize_form.setRowVisible(widget, not scaled)
        self.fit_controls()

    def fit_controls(self):
        page = self.tabs.currentWidget()
        self.tabs.setFixedHeight(page.sizeHint().height() + self.tabs.tabBar().sizeHint().height() + 8)

    def sync_resize_size(self, axis):
        self.resize_axis = axis
        self.resize_target = self.resize_width.value() if axis == 'width' else self.resize_height.value()
        if self.current is None or not self.keep_ratio.isChecked():
            return
        h, w = self.current.shape[:2]
        # Làm tròn giống thuật toán Resize, lấy chiều vừa sửa làm chuẩn.
        ratio = self.resize_width.value() / w if axis == 'width' else self.resize_height.value() / h
        with QSignalBlocker(self.resize_width), QSignalBlocker(self.resize_height):
            self.resize_width.setValue(max(1, int(w * ratio)))
            self.resize_height.setValue(max(1, int(h * ratio)))

    def build_rotate(self):
        form = self.tab_form('Rotate')
        self.angle = spin(0, -360, 360, True)
        self.rotate_scale = spin(1, .01, 10, True)
        self.keep_full = QCheckBox('Keep Full Image · Giữ toàn bộ ảnh')
        self.keep_full.setChecked(True)
        self.rotate_interp = combo(PERSPECTIVE_INTERPOLATIONS)
        for name, widget in [('Góc (độ)', self.angle), ('Scale', self.rotate_scale),
                ('', self.keep_full), ('Nội suy', self.rotate_interp)]:
            form.addRow(name, widget)
        form.addRow(QLabel('Góc dương: ngược chiều kim đồng hồ.'))

    def build_perspective(self):
        form = self.tab_form('Perspective')
        label = QLabel('Chọn 4 góc tài liệu trên ảnh Before.\nCó thể kéo các điểm để chỉnh lại.')
        label.setWordWrap(True)
        form.addRow(label)
        clear = QPushButton('Xóa điểm')
        clear.clicked.connect(self.clear_points)
        form.addRow(clear)
        full = QPushButton('Chọn toàn bộ ảnh')
        full.clicked.connect(self.default_points)
        form.addRow(full)
        self.persp_width = spin(0, 0, 24000)
        self.persp_height = spin(0, 0, 24000)
        self.persp_width.setSpecialValueText('Tự động')
        self.persp_height.setSpecialValueText('Tự động')
        self.persp_interp = combo(PERSPECTIVE_INTERPOLATIONS)
        for name, widget in [('Rộng đầu ra', self.persp_width), ('Cao đầu ra', self.persp_height),
            ('Nội suy', self.persp_interp)]:
            form.addRow(name, widget)

    def error(self, message):
        self.update_summary('Lỗi · ' + message)
        QMessageBox.warning(self, 'Không thể thực hiện', message)

    def set_busy(self, busy):
        self.controls.setEnabled(not busy)
        self.open_button.setEnabled(not busy)
        self.video_button.setEnabled(not busy)
        self.video_bar.setEnabled(not busy)
        self.reset_button.setEnabled(not busy and self.current is not None)
        self.apply_button.setEnabled(not busy and self.current is not None)
        self.save_button.setEnabled(not busy and self.result is not None)
        self.before.setEnabled(not busy)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Mở ảnh tài liệu', '',
            'Ảnh (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Tất cả (*)')
        if path:
            self.load_image(path)

    def load_image(self, path):
        try:
            image = read_image(path)
            self.close_video()
            self.accept_source(image, str(path))
        except Exception as exc:
            self.error(str(exc))

    def close_video(self):
        if self.video is not None:
            self.video.release()
        self.video = None
        self.video_path = None
        self.video_bar.hide()

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Mở video để chọn khung hình', '',
                                             'Video (*.mp4 *.avi *.mov *.mkv);;Tất cả (*)')
        if not path:
            return
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            capture.release()
            self.error('Không mở được video hoặc codec không được hỗ trợ.')
            return
        self.close_video()
        self.video, self.video_path = capture, path
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_index.setMaximum(max(0, count-1))
        self.frame_index.setValue(0)
        self.video_bar.show()
        self.read_frame()

    def read_frame(self):
        if self.video is None:
            return
        index = self.frame_index.value()
        self.video.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self.video.read()
        if not ok:
            self.error('Không đọc được khung hình này.')
            return
        try:
            validate_image(frame)
            self.accept_source(frame, f'{self.video_path} · frame {index}')
        except ValueError as exc:
            self.error(str(exc))

    def accept_source(self, image, source):
        self.source = source
        self.set_current(image)
        self.statusBar().showMessage(f'{source} · {image.shape[1]}×{image.shape[0]} px')

    def reset_image(self):
        if self.current is not None:
            self.set_current(self.current)

    def set_current(self, image):
        self.current = image
        self.result = None
        self.info = {}
        self.before.set_image(image)
        self.after.set_image(None)
        self.metrics.setRowCount(0)
        self.update_details()
        h, w = image.shape[:2]
        self.resize_axis = 'width'
        self.resize_target = w
        with QSignalBlocker(self.resize_width), QSignalBlocker(self.resize_height):
            self.resize_width.setValue(w)
            self.resize_height.setValue(h)
        self.clear_points()
        self.mode_changed()
        self.set_busy(False)
        self.update_summary('Sẵn sàng')

    def default_points(self):
        if self.current is not None:
            h, w = self.current.shape[:2]
            self.before.set_points([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
            self.sync_points(self.before.points)

    def clear_points(self):
        self.before.set_points([])
        self.sync_points([])

    def sync_points(self, points):
        if len(points) != 4:
            message = f'Đã chọn {len(points)}/4 góc · Hãy chọn đủ 4 góc trên ảnh Before.'
        else:
            try:
                order_points(points)
                message = 'Đã chọn 4/4 góc · Kéo nút tròn để chỉnh vị trí.'
            except ValueError as exc:
                message = str(exc)
        self.point_status.setText(message)

    def mode_changed(self):
        self.fit_controls()
        self.apply_button.setText('Áp dụng ' + self.tabs.tabText(self.tabs.currentIndex()))
        self.before.editable = self.tabs.currentIndex() == 2
        self.before.redraw_points()
        self.point_status.setVisible(self.before.editable)
        self.update_summary()

    def parameters(self):
        mode = self.tabs.currentIndex()
        if mode == 0:
            params = {'interpolation': self.resize_interp.currentText()}
            if self.resize_mode.currentIndex() == 0:
                params['scale'] = self.resize_scale.value()
            else:
                params['keep_aspect_ratio'] = self.keep_ratio.isChecked()
                if self.keep_ratio.isChecked():
                    # Chỉ truyền chiều vừa sửa để tránh làm tròn hai lần.
                    params[self.resize_axis] = self.resize_target
                else:
                    params.update(width=self.resize_width.value(), height=self.resize_height.value())
            return 'Resize', params
        if mode == 1:
            return 'Rotate', {'angle': self.angle.value(), 'scale': self.rotate_scale.value(),
                'keep_full': self.keep_full.isChecked(), 'interpolation': self.rotate_interp.currentText()}
        return 'Perspective', {'points': np.asarray(self.before.points, dtype=np.float32),
            'output_width': self.persp_width.value() or None, 'output_height': self.persp_height.value() or None,
            'interpolation': self.persp_interp.currentText()}

    def apply_transform(self):
        if self.current is None:
            self.update_summary('Hãy mở ảnh trước khi áp dụng')
            return
        if self.worker and self.worker.isRunning():
            return
        operation, params = self.parameters()
        self.result = None
        self.info = {}
        self.after.set_image(None)
        self.metrics.setRowCount(0)
        self.update_details()
        self.set_busy(True)
        self.update_summary('Đang xử lý…')
        self.statusBar().showMessage(f'Đang chạy {operation}…')
        self.worker = TransformWorker(self.current, operation, params)
        self.worker.result_ready.connect(self.show_result)
        self.worker.failed.connect(self.error)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def worker_finished(self):
        self.set_busy(False)
        self.update_summary('Hoàn tất' if self.result is not None else 'Lỗi · Kiểm tra tham số')
        self.statusBar().showMessage('Đã xử lý xong.' if self.result is not None else 'Chưa có kết quả; hãy kiểm tra tham số.')

    def show_result(self, result, info):
        self.result, self.info = result, info
        self.after.set_image(result)
        operation = info['Phép biến đổi']
        if operation == 'Resize':
            keys = ['MSE', 'PSNR (dB)', 'SSIM (cửa sổ)']
        elif operation == 'Rotate':
            keys = ['Góc (độ, dương = ngược kim đồng hồ)', 'Scale xoay', 'Giữ toàn bộ']
        else:
            keys = ['sharpness', 'selected_area_ratio', 'reprojection_max_px']
        labels = {'sharpness': 'Độ sắc nét (Laplacian)',
                  'selected_area_ratio': 'Diện tích chọn / ảnh',
                  'reprojection_max_px': 'Sai số chiếu lại lớn nhất (px)'}
        entries = [(labels.get(key, key), info[key]) for key in keys]
        self.metrics.setRowCount(len(entries))
        for row, (key, value) in enumerate(entries):
            if isinstance(value, float):
                text = f'{value:.5g}'
            elif value is None:
                text = 'Không áp dụng (ảnh quá nhỏ)'
            else:
                text = str(value)
            self.metrics.setItem(row, 0, QTableWidgetItem(key))
            self.metrics.setItem(row, 1, QTableWidgetItem(text))
        self.metrics.resizeRowsToContents()
        self.evaluation_note.setText(info.get('Ghi chú', 'Keep Full mở rộng canvas để giữ mép ảnh khi xoay.'))
        self.update_details()
        self.update_summary('Hoàn tất')

    def update_details(self):
        self.details_toggle.setEnabled(bool(self.info))
        visible = bool(self.info) and self.details_toggle.isChecked()
        self.metrics.setVisible(visible)
        self.evaluation_note.setVisible(visible)

    def update_summary(self, status=None):
        if status is not None:
            self.result_status = status
        operation = self.info.get('Phép biến đổi', self.tabs.tabText(self.tabs.currentIndex()))
        input_size = '—' if self.current is None else f'{self.current.shape[1]}×{self.current.shape[0]}'
        output_size = self.info.get('Đầu ra (W×H)', '—')
        elapsed = self.info.get('Thời gian biến đổi và kiểm tra (ms)')
        duration = '—' if elapsed is None else f'{elapsed:.1f} ms'
        self.summary.setText(f'Tool: {operation} | Input: {input_size} | Output: {output_size} | '
                             f'Time: {duration} | Status: {self.result_status}')

    def save_image(self):
        if self.result is None:
            self.update_summary('Chưa có kết quả để lưu')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu kết quả', 'scan_result.png',
                'PNG (*.png);;JPEG (*.jpg);;TIFF (*.tiff);;BMP (*.bmp)')
        if path:
            try:
                if not Path(path).suffix:
                    path += '.png'
                write_image(path, self.result)
                self.statusBar().showMessage(f'Đã lưu: {path}')
            except Exception as exc:
                self.error(str(exc))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage('Đang xử lý; hãy đóng cửa sổ sau khi tác vụ kết thúc.')
            event.ignore()
            return
        self.close_video()
        super().closeEvent(event)
