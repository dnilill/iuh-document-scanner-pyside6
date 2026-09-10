"""Chạy: python main.py [đường_dẫn_ảnh]."""
import sys
from PySide6.QtWidgets import QApplication
from scan_app.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.load_image(sys.argv[1])
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
