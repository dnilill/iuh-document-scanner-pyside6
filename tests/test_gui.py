import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
from pathlib import Path
import numpy as np
import cv2
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QPointF
from PySide6.QtTest import QTest
from PySide6.QtGui import QFontDatabase, QPalette, QColor
from scan_app.window import MainWindow
from scan_app.image_io import write_image, read_image


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    font = Path('C:/Windows/Fonts/segoeui.ttf')
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
    return application


def finish_worker(app, window):
    deadline = time.monotonic() + 15
    while window.worker.isRunning() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert window.worker.wait(1000)
    app.processEvents()
    assert window.result is not None
    assert window.save_button.isEnabled()


def test_gui_workflow(app, tmp_path, monkeypatch):
    window = MainWindow()
    errors = []
    window.error = errors.append
    window.show()
    image = np.random.default_rng(7).integers(0, 255, (180, 240, 3), np.uint8)
    source = tmp_path / 'ảnh gốc.png'
    write_image(source, image)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(source), 'PNG'))
    window.open_image()
    app.processEvents()
    window.resize_scale.setValue(.5)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape == (90, 120, 3)
    window.tabs.setCurrentIndex(1)
    window.angle.setValue(90)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape == (240, 180, 3)
    target = tmp_path / 'kết quả.png'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(target), 'PNG'))
    window.save_image()
    np.testing.assert_array_equal(read_image(target), window.result)
    window.reset_image()
    np.testing.assert_array_equal(window.current, image)
    window.tabs.setCurrentIndex(2)
    window.clear_points()
    app.processEvents()
    # Click through actual scene-to-viewport mapping after resizing the window.
    for x, y in [(10, 10), (220, 12), (215, 160), (12, 165)]:
        position = window.before.mapFromScene(QPointF(x, y))
        QTest.mouseClick(window.before.viewport(), Qt.MouseButton.LeftButton, pos=position)
    assert len(window.before.points) == 4
    np.testing.assert_allclose(window.before.points[0], [10, 10], atol=2)
    window.apply_transform()
    finish_worker(app, window)
    assert window.info['reprojection_max_px'] < 1e-3
    target = tmp_path / 'scan tài liệu.png'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(target), 'PNG'))
    window.save_image()
    np.testing.assert_array_equal(read_image(target), window.result)
    assert errors == []
    Path('tmp').mkdir(exist_ok=True)
    window.grab().save('tmp/gui-test.png')
    window.close()


def test_light_mode_overrides_dark_palette(app):
    # Giả lập màu tối trước khi mở app, không đổi cài đặt Windows.
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Window, QColor('#202020'))
    dark.setColor(QPalette.ColorRole.Base, QColor('#101010'))
    dark.setColor(QPalette.ColorRole.Text, QColor('#ffffff'))
    app.setPalette(dark)
    window = MainWindow()
    window.show()
    app.processEvents()
    # Qt offscreen không báo theme hệ điều hành; kiểm tra palette bên dưới.
    if app.platformName() != 'offscreen':
        assert app.styleHints().colorScheme() == Qt.ColorScheme.Light
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive,
                  QPalette.ColorGroup.Disabled):
        assert app.palette().color(group, QPalette.ColorRole.Base).lightness() > 200
        assert app.palette().color(group, QPalette.ColorRole.Text).lightness() < 150
    for widget in [window, window.tabs, window.resize_interp, window.resize_width,
                   window.angle, window.keep_ratio, window.save_button, window.before]:
        assert widget.palette().color(QPalette.ColorRole.Window).lightness() > 200
    window.tabs.setCurrentIndex(2)
    assert window.before.points == []
    assert window.apply_button.text() == 'Áp dụng Perspective'
    window.close()


def test_unreadable_image_keeps_current_source(app, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: errors.append(args[-1]))
    window = MainWindow()
    image = np.zeros((60, 90, 3), np.uint8)
    window.accept_source(image, 'valid image')
    invalid = tmp_path / 'ảnh lỗi.png'
    invalid.write_text('not an image', encoding='utf-8')
    window.load_image(invalid)
    assert errors
    np.testing.assert_array_equal(window.current, image)
    window.close()


def test_video_frame_selection(app, tmp_path, monkeypatch):
    path = tmp_path / 'khung hình tiếng Việt.avi'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 5, (80, 60))
    assert writer.isOpened()
    for value in [20, 80, 150]:
        writer.write(np.full((60, 80, 3), value, np.uint8))
    writer.release()
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), 'Video'))
    window = MainWindow()
    window.open_video()
    assert window.frame_index.maximum() == 2
    window.frame_index.setValue(2)
    window.read_frame()
    assert abs(float(window.current.mean())-150) < 3
    assert 'frame 2' in window.source
    window.close()


def test_resize_dimensions_and_new_source(app):
    window = MainWindow()
    window.accept_source(np.zeros((60, 90, 3), np.uint8), 'first')
    window.resize_mode.setCurrentIndex(1)
    for axis, value in [('width', 61), ('height', 47)]:
        getattr(window, 'resize_' + axis).setValue(value)
        expected = (window.resize_height.value(), window.resize_width.value())
        window.apply_transform()
        finish_worker(app, window)
        assert window.result.shape[:2] == expected
        assert abs(expected[1] / expected[0] - 1.5) < .05
    window.keep_ratio.setChecked(False)
    window.resize_width.setValue(100)
    window.resize_height.setValue(100)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape[:2] == (100, 100)
    window.keep_ratio.setChecked(True)
    assert window.resize_width.value() == 150
    window.accept_source(np.zeros((75, 125, 3), np.uint8), 'second')
    assert (window.resize_width.value(), window.resize_height.value()) == (125, 75)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape[:2] == (75, 125)
    window.close()


def test_tool_visibility_and_result_summary(app):
    window = MainWindow()
    window.show()
    window.accept_source(np.zeros((60, 90, 3), np.uint8), 'image')
    app.processEvents()
    assert window.resize_scale.isVisible()
    assert not window.resize_width.isVisible()
    assert not window.angle.isVisible()
    assert not window.persp_width.isVisible()
    window.resize_mode.setCurrentIndex(1)
    assert window.resize_width.isVisible()
    assert not window.resize_scale.isVisible()
    window.apply_transform()
    finish_worker(app, window)
    assert not window.metrics.isVisible()
    window.details_toggle.setChecked(True)
    assert window.metrics.isVisible()
    assert [window.metrics.item(i, 0).text() for i in range(3)] == ['MSE', 'PSNR (dB)', 'SSIM (cửa sổ)']
    window.tabs.setCurrentIndex(1)
    assert window.angle.isVisible()
    assert not window.resize_width.isVisible()
    assert 'Tool: Resize' in window.summary.text()  # Summary still describes the displayed result.
    window.angle.setValue(90)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape[:2] == (90, 60)
    assert 'Input: 90×60 | Output: 60×90' in window.summary.text()
    assert 'Time:' in window.summary.text() and 'Hoàn tất' in window.summary.text()
    assert all(window.metrics.item(i, 0).text() not in ['MSE', 'PSNR (dB)', 'SSIM (cửa sổ)'] for i in range(3))
    window.tabs.setCurrentIndex(2)
    assert window.persp_width.isVisible() and window.point_status.isVisible()
    assert not window.angle.isVisible()
    window.close()


@pytest.mark.parametrize('points', [[], [[0, 0], [20, 0], [20, 20]],
                                     [[0, 0], [0, 0], [20, 20], [0, 20]]])
def test_invalid_perspective_recovers(app, monkeypatch, points):
    errors = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: errors.append(args[-1]))
    window = MainWindow()
    window.accept_source(np.zeros((60, 90, 3), np.uint8), 'image')
    window.apply_transform()
    finish_worker(app, window)
    window.tabs.setCurrentIndex(2)
    window.before.set_points(points)
    window.sync_points(points)
    assert '4/4 góc' not in window.point_status.text()
    window.apply_transform()
    deadline = time.monotonic() + 15
    while window.worker.isRunning() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert window.worker.wait(1000)
    app.processEvents()
    assert errors
    assert window.result is None and not window.save_button.isEnabled()
    assert 'Lỗi' in window.summary.text()
    window.default_points()
    window.apply_transform()
    finish_worker(app, window)
    window.close()


def test_empty_actions_and_reset(app, monkeypatch):
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: pytest.fail('No result to save'))
    window = MainWindow()
    window.apply_transform()
    window.save_image()
    window.reset_image()
    window.clear_points()
    assert window.worker is None
    assert not window.apply_button.isEnabled() and not window.save_button.isEnabled()
    window.accept_source(np.zeros((60, 90, 3), np.uint8), 'image')
    window.apply_transform()
    finish_worker(app, window)
    window.reset_image()
    assert window.result is None and window.info == {}
    assert window.after.pixmap is None and not window.metrics.isVisible()
    assert 'Output: —' in window.summary.text()
    window.close()


def test_drag_points_after_window_resize_and_bgr_display(app):
    window = MainWindow()
    image = np.zeros((180, 240, 3), np.uint8)
    image[:] = [10, 50, 230]
    window.accept_source(image, 'color')
    color = window.before.pixmap.pixmap().toImage().pixelColor(100, 100)
    assert (color.red(), color.green(), color.blue()) == (230, 50, 10)
    window.tabs.setCurrentIndex(2)
    window.before.set_points([[20, 20], [220, 20], [220, 160], [20, 160]])
    window.show()
    window.resize(1100, 750)
    app.processEvents()
    start = window.before.mapFromScene(QPointF(20, 20))
    end = window.before.mapFromScene(QPointF(40, 35))
    QTest.mousePress(window.before.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.before.viewport(), end)
    QTest.mouseRelease(window.before.viewport(), Qt.MouseButton.LeftButton, pos=end)
    np.testing.assert_allclose(window.before.points[0], [40, 35], atol=2)
    assert window.before.drag_index is None
    assert len(window.before.overlays) == 9  # Polygon + four circles + four labels.
    assert '4/4 góc' in window.point_status.text()
    window.apply_transform()
    finish_worker(app, window)
    window.close()
