"""Launch the PriVis native Qt Widgets application."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> int:
    # The sidebar and content have an explicit light-theme palette.
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setApplicationName("PriVis")
    fonts = set(QFontDatabase.families())
    if "Inter" in fonts:
        app.setFont(QFont("Inter", 13))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
