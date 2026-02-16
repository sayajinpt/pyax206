import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QImage
from PyQt6.QtCore import Qt, QTimer, QPoint

from pyax206 import AX206Display


class DrawWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AX206 Live Draw")
        self.setGeometry(100, 100, 800, 600)

        self.image = QImage(self.size(), QImage.Format.Format_RGB888)
        self.image.fill(QColor(20, 20, 25))

        self.last_point = QPoint()
        self.drawing = False

        self.pen_color = QColor(0, 255, 255)
        self.pen_width = 4

        # Open display
        self.display = AX206Display(rotation=0, fps_limit=3).open()

        # Timer for streaming
        self.timer = QTimer()
        self.timer.timeout.connect(self.stream_to_lcd)
        self.timer.start(100)  # ~10 FPS capture → LCD limits to ~3

    # ---------------- Mouse Events ----------------

    def mousePressEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.last_point = event.position().toPoint()
            self.drawing = True

    def mouseMoveEvent(self, event):
        if self.drawing:
            painter = QPainter(self.image)
            pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            current_point = event.position().toPoint()
            painter.drawLine(self.last_point, current_point)
            self.last_point = current_point
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    # ---------------- Paint ----------------

    def paintEvent(self, event):
        canvas_painter = QPainter(self)
        canvas_painter.drawImage(self.rect(), self.image, self.image.rect())

    # ---------------- Stream to LCD ----------------

    def stream_to_lcd(self):
        # Convert QImage to numpy
        w = self.image.width()
        h = self.image.height()

        ptr = self.image.bits()
        ptr.setsize(self.image.sizeInBytes())
        arr = np.array(ptr, dtype=np.uint8).reshape((h, w, 3))

        # Send to display (library handles resize + rotation)
        self.display.show_numpy_bgr(arr[:, :, ::-1])  # RGB -> BGR

    def closeEvent(self, event):
        self.display.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DrawWidget()
    window.show()
    sys.exit(app.exec())
