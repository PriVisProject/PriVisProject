"""Launch the PriVis native Qt Widgets application."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QDialog

from data_loader import DEFAULT_DATA_FOLDER
from main_window import MainWindow
from startup import StartupDialog


def main() -> int:
    # The sidebar and content have an explicit light-theme palette.
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setApplicationName("PriVis")
    fonts = set(QFontDatabase.families())
    if "Inter" in fonts:
        app.setFont(QFont("Inter", 13))
    startup = StartupDialog()
    while startup.exec() == QDialog.DialogCode.Accepted:
        data_folder = None if startup.start_empty else DEFAULT_DATA_FOLDER
        window = MainWindow(data_folder=data_folder)
        logged_out = False

        def logout():
            nonlocal logged_out
            logged_out = True
            window.close()

        window.advanced.logout_button.clicked.connect(logout)
        window.show()
        exit_code = app.exec()
        window.advanced.logout_button.clicked.disconnect(logout)
        window.deleteLater()
        if not logged_out:
            return exit_code
        startup.show_login(start_empty=startup.start_empty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
