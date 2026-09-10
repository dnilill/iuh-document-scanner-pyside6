import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import time
from pathlib import Path
import numpy as np
import cv2
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QFontDatabase
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
    window.load_image(source)
    app.processEvents()
    window.resize_scale.setValue(.5)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape == (90, 120, 3)
    window.commit_result()
    window.tabs.setCurrentIndex(1)
    window.angle.setValue(90)
    window.apply_transform()
    finish_worker(app, window)
    assert window.result.shape == (120, 90, 3)
    target = tmp_path / 'kết quả.png'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(target), 'PNG'))
    window.save_image()
    np.testing.assert_array_equal(read_image(target), window.result)
    report = tmp_path / 'đánh giá.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(report), 'JSON'))
    window.save_report()
    saved = json.loads(report.read_text(encoding='utf-8'))
    assert len(saved['committed_steps']) == 1
    assert saved['current_result']['Phép biến đổi'] == 'Rotate'
    window.reset_image()
    np.testing.assert_array_equal(window.current, image)
    window.tabs.setCurrentIndex(2)
    window.clear_points()
    app.processEvents()
    # Click through actual scene-to-viewport mapping after resizing the window.
    from PySide6.QtCore import QPointF
    for x, y in [(10, 10), (220, 12), (215, 160), (12, 165)]:
        position = window.before.mapFromScene(QPointF(x, y))
        QTest.mouseClick(window.before.viewport(), Qt.MouseButton.LeftButton, pos=position)
    assert len(window.before.points) == 4
    np.testing.assert_allclose(window.before.points[0], [10, 10], atol=2)
    window.apply_transform()
    finish_worker(app, window)
    assert window.info['reprojection_max_px'] < 1e-3
    assert errors == []
    Path('tmp').mkdir(exist_ok=True)
    window.grab().save('tmp/gui-test.png')
    window.close()


def test_video_frame_selection(app, tmp_path, monkeypatch):
    path = tmp_path / 'video.avi'
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
