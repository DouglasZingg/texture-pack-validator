import sys
from PySide6.QtWidgets import QApplication

from validator.ui.main_window import MainWindow


def run_app() -> int:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    return app.exec()
