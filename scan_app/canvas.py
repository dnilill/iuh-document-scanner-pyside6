"""Canvas dùng tọa độ ảnh qua QGraphicsView.mapToScene."""
import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


class ImageCanvas(QGraphicsView):
    points_changed = Signal(object)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumSize(230, 250)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setBackgroundBrush(QColor('#e9eef3'))
        self.pixmap = None
        self.points = []
        self.overlays = []
        self.editable = False
        self.drag_index = None

    def set_image(self, image):
        self.scene().clear()
        self.overlays = []
        self.points = []
        self.pixmap = None
        if image is not None:
            rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            qimage = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0],
                            QImage.Format.Format_RGB888).copy()
            self.pixmap = self.scene().addPixmap(QPixmap.fromImage(qimage))
            self.scene().setSceneRect(self.pixmap.boundingRect())
            self.fit_image()

    def fit_image(self):
        if self.pixmap:
            self.fitInView(self.pixmap, Qt.AspectRatioMode.KeepAspectRatio)
            self.redraw_points()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_image()

    def set_points(self, points):
        self.points = [list(map(float, p)) for p in points]
        self.redraw_points()

    def redraw_points(self):
        for item in self.overlays:
            self.scene().removeItem(item)
        self.overlays = []
        if not self.editable:
            return
        scale = max(self.transform().m11(), 0.001)
        pen = QPen(QColor('#009f89'), 2)
        pen.setCosmetic(True)
        if len(self.points) == 4:
            from .algorithms import order_points
            try:
                polygon_points = order_points(self.points)
            except ValueError:
                polygon_points = self.points
            poly = QPolygonF([QPointF(x, y) for x, y in polygon_points])
            self.overlays.append(self.scene().addPolygon(poly, pen))
        for i, (x, y) in enumerate(self.points):
            r = 6 / scale
            item = self.scene().addEllipse(x-r, y-r, 2*r, 2*r, pen, QColor('#ffffff'))
            self.overlays.append(item)
            text = self.scene().addText(str(i+1))
            text.setDefaultTextColor(QColor('#00695c'))
            text.setScale(1/scale)
            text.setPos(x+8/scale, y+4/scale)
            self.overlays.append(text)

    def image_point(self, event):
        point = self.mapToScene(event.position().toPoint())
        bounds = self.pixmap.boundingRect()
        return [min(max(point.x(), 0), bounds.width()-1),
                min(max(point.y(), 0), bounds.height()-1)]

    def mousePressEvent(self, event):
        if self.editable and self.pixmap and event.button() == Qt.MouseButton.LeftButton:
            p = self.image_point(event)
            if self.points:
                distances = np.linalg.norm(np.asarray(self.points) - p, axis=1)
                index = int(np.argmin(distances))
                if distances[index] * self.transform().m11() < 18:
                    self.drag_index = index
            if self.drag_index is None and len(self.points) < 4:
                self.points.append(p)
                self.drag_index = len(self.points)-1
                self.points_changed.emit(self.points)
                self.redraw_points()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_index is not None:
            self.points[self.drag_index] = self.image_point(event)
            self.redraw_points()
            self.points_changed.emit(self.points)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_index = None
        super().mouseReleaseEvent(event)
