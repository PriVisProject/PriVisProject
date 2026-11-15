"""Main window and section navigation for PriVis."""

from datetime import date
import logging
from pathlib import Path

from PySide6.QtCore import QSize, QThread, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


from advanced_page import AdvancedPage
from data_loader import DEFAULT_DATA_FOLDER, DataValidationError
from review_pages import Overview, RISK_COLORS, ReviewTable, load_review
from simulation_page import SimulationPage
from visual_theme import icon


LOGGER = logging.getLogger(__name__)

WINDOW_STYLE = """
QWidget#sidebar { background: #101C30; }
QWidget#content, QStackedWidget { background: #F5F8FC; color: #24364B; }
QLabel#wordmark { color: #F5F8FC; font-size: 32px; font-weight: 700; }
QLabel#brandMark { background: #24364B; border-radius: 9px; }
QLabel#tagline { color: #B8C8DB; font-size: 12px; }
QFrame#sidebarDivider { background: #34475D; max-height: 1px; }
QPushButton[nav="true"] {
    text-align: left; padding: 11px 12px; border: 1px solid transparent; outline: none;
    border-radius: 7px; color: #B8C8DB; background: transparent; font-size: 15px;
}
QPushButton[nav="true"]:hover { background: #1A2B41; }
QPushButton[nav="true"]:checked {
    color: #F5F8FC; background: #24364B; border-left: 3px solid #17B8A6;
    padding-left: 10px; font-weight: 600;
}
QPushButton[nav="true"]:focus { border-top-color: #55D6CB; border-bottom-color: #55D6CB; }
QLabel#pageTitle { color: #101C30; font-size: 32px; font-weight: 700; }
QFrame#sectionCard { background: white; border: 1px solid #DCE4EE; border-radius: 12px; }
QLabel#metricValue { color: #101C30; font-size: 34px; font-weight: 700; }
QLabel#metricCaption, QLabel#rowCount { color: #627995; }
QLabel#sectionTitle { color: #101C30; font-size: 17px; font-weight: 650; }
QLabel#sourceStatus { color: #DCE4EE; font-size: 12px; }
QPushButton#openFolder {
    background: #24364B; color: #F5F8FC; border: 1px solid #627995;
    border-radius: 7px; padding: 9px; outline: none;
}
QPushButton#openFolder:hover, QPushButton#openFolder:focus { border-color: #55D6CB; }
QPushButton#openFolder:disabled { color: #A8B9CC; }
QLineEdit, QPlainTextEdit, QTextEdit, QTableView {
    background: white; color: #24364B; border: 1px solid #DCE4EE;
    border-radius: 8px; selection-background-color: #D9F4EF;
    selection-color: #101C30;
}
QLineEdit { padding: 7px 10px; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QTableView:focus { border-color: #17B8A6; }
QPlainTextEdit, QTextEdit { padding: 9px; }
QTableView {
    alternate-background-color: #F5F8FC;
    selection-background-color: transparent;
    selection-color: #24364B;
}
QTableView::item:selected { background: transparent; }
QTableView::item { padding: 0 8px; }
QHeaderView::section {
    background: #EAF0F7; color: #24364B; border: 0;
    border-bottom: 1px solid #DCE4EE; padding: 9px 7px; font-weight: 600;
}
QComboBox {
    background: white; color: #24364B; border: 1px solid #DCE4EE;
    border-radius: 8px; padding: 7px 30px 7px 10px;
}
QComboBox:hover, QComboBox:focus, QComboBox:on { border-color: #17B8A6; }
QComboBox:disabled { background: #EAF0F7; color: #627995; }
QComboBox::drop-down { width: 28px; border: 0; }
QComboBox::down-arrow { image: none; width: 0; height: 0; }
QComboBox QAbstractItemView {
    background: white; color: #24364B; border: 1px solid #DCE4EE;
    padding: 4px; selection-background-color: #D9F4EF; selection-color: #101C30;
}
QTabWidget::pane { border: 0; }
QTabBar::tab {
    background: #EAF0F7; color: #24364B; border: 1px solid #DCE4EE;
    border-radius: 8px; padding: 8px 14px; margin: 0 6px 8px 0;
    font-weight: 600; outline: none;
}
QTabBar::tab:hover { background: #DCE4EE; }
QTabBar::tab:selected { background: #D9F4EF; border-color: #A5DBD2; color: #101C30; }
QTabBar::tab:focus { border-color: #088D80; }
QScrollBar:vertical, QScrollBar:horizontal {
    background: #F5F8FC; border: 0; border-radius: 6px;
}
QScrollBar:vertical { width: 12px; margin: 3px 0; }
QScrollBar:horizontal { height: 12px; margin: 0 3px; }
QScrollBar::handle {
    background: #93A6BA; border: 2px solid #F5F8FC; border-radius: 6px;
}
QScrollBar::handle:vertical { min-height: 26px; }
QScrollBar::handle:horizontal { min-width: 26px; }
QScrollBar::handle:hover { background: #627995; }
QScrollBar::handle:pressed { background: #088D80; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSplitter::handle { background: #DCE4EE; }
QPushButton#previewRemoval, QPushButton#resetSimulation, QPushButton[solutionAction="true"] {
    color: #101C30; background: #17B8A6; border: 1px solid #088D80;
    border-radius: 8px; padding: 8px 14px; font-weight: 600;
}
QPushButton#previewRemoval:hover, QPushButton[solutionAction="true"]:hover { background: #55D6CB; }
QPushButton#resetSimulation { background: white; border-color: #DCE4EE; }
QPushButton#resetSimulation:hover { background: #EAF0F7; }
QPushButton#previewRemoval:focus, QPushButton#resetSimulation:focus, QPushButton[solutionAction="true"]:focus { border-color: #101C30; }
QPushButton#previewRemoval:disabled, QPushButton#resetSimulation:disabled, QPushButton[solutionAction="true"]:disabled {
    background: #EAF0F7; border-color: #DCE4EE; color: #627995;
}
"""


class ReviewLoadThread(QThread):
    def __init__(self, folder, review_date, parent):
        super().__init__(parent)
        self.folder = folder
        self.review_date = review_date
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = load_review(self.folder, self.review_date)
        except (DataValidationError, OSError) as error:
            LOGGER.warning("Data folder rejected: %s", error)
            self.error = str(error)
        except Exception:
            LOGGER.exception("Unexpected data loading error")
            self.error = "An unexpected error occurred while loading the dataset."


class MainWindow(QMainWindow):
    """Display each section in a persistent page selected by sidebar buttons."""

    def __init__(self, data_folder=DEFAULT_DATA_FOLDER, *, review_date=None):
        super().__init__()
        self.review_date = review_date
        self.data_folder = None
        self._load_thread = None
        self._close_after_load = False
        self.setWindowTitle("PriVis")
        self.setMinimumSize(780, 555)
        self.resize(1100, 710)
        self.setWindowIcon(icon("PriVis"))

        content = QWidget()
        content.setObjectName("content")
        layout = QHBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(content)
        self.setStyleSheet(WINDOW_STYLE)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(238)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 27, 18, 18)
        sidebar_layout.setSpacing(6)

        self._heading_font = None
        if "Space Grotesk" in QFontDatabase.families():
            self._heading_font = QFont("Space Grotesk")

        brand_row = QHBoxLayout()
        mark = QLabel()
        mark.setObjectName("brandMark")
        mark.setFixedSize(38, 38)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setPixmap(icon("PriVis").pixmap(QSize(24, 24)))
        brand_row.addWidget(mark)
        wordmark = self._heading('Pri<span style="color:#55D6CB">Vis</span>', "wordmark")
        wordmark.setAccessibleName("PriVis")
        brand_row.addWidget(wordmark, 1)
        sidebar_layout.addLayout(brand_row)
        tagline = QLabel("See the Access. Reduce the Risk.")
        tagline.setObjectName("tagline")
        tagline.setWordWrap(True)
        sidebar_layout.addWidget(tagline)
        sidebar_layout.addSpacing(12)
        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)
        sidebar_layout.addWidget(divider)
        sidebar_layout.addSpacing(16)

        self.pages = QStackedWidget()
        self.navigation = QButtonGroup(self)
        self.navigation.idClicked.connect(self.pages.setCurrentIndex)
        self.overview = Overview()
        self.users = ReviewTable(
            ("Name", "Account ID", "Department", "Role", "Worker type", "Status"),
            5, "All statuses", ("Enabled", "Disabled"),
        )
        self.groups = ReviewTable(
            ("Group", "Description", "Risk"), 2, "All risk levels", RISK_COLORS,
        )
        self.findings = ReviewTable(
            ("Severity", "User", "Group", "Finding"), 0, "All severities", RISK_COLORS,
        )
        self.simulations = SimulationPage()
        self.advanced = AdvancedPage()
        sections = (
            ("Overview", self.overview), ("Users", self.users), ("Groups", self.groups),
            ("Findings", self.findings), ("Simulations", self.simulations),
            ("Advanced", self.advanced),
        )
        for name, widget in sections:
            index = self.pages.addWidget(self._section_page(name, widget))
            button = QPushButton(name)
            button.setProperty("nav", True)
            button.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
            button.setIconSize(QSize(21, 21))
            button.setIcon(icon(name, "#B8C8DB"))
            active_icon = icon(name)
            idle_icon = button.icon()
            button.toggled.connect(
                lambda active, button=button, on=active_icon, off=idle_icon:
                button.setIcon(on if active else off)
            )
            button.setCheckable(True)
            sidebar_layout.addWidget(button)
            self.navigation.addButton(button, index)

        self.navigation.button(0).setChecked(True)
        sidebar_layout.addStretch()
        self.source_status = QLabel()
        self.source_status.setObjectName("sourceStatus")
        self.source_status.setTextFormat(Qt.TextFormat.PlainText)
        self.source_status.setWordWrap(True)
        sidebar_layout.addWidget(self.source_status)
        self.open_folder = QPushButton("Open Data Folder…")
        self.open_folder.setObjectName("openFolder")
        self.open_folder.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.open_folder.clicked.connect(self.choose_folder)
        sidebar_layout.addWidget(self.open_folder)
        layout.addWidget(sidebar)
        content_column = QVBoxLayout()
        content_column.setContentsMargins(0, 0, 0, 0)
        self.load_error = QLabel()
        self.load_error.setTextFormat(Qt.TextFormat.PlainText)
        self.load_error.setWordWrap(True)
        self.load_error.setMargin(12)
        self.load_error.setStyleSheet("background: #FCE8EC; color: #78283A;")
        self.load_error.hide()
        content_column.addWidget(self.load_error)
        content_column.addWidget(self.pages, stretch=1)
        layout.addLayout(content_column, stretch=1)
        self.load_folder(data_folder)

    def choose_folder(self):
        start = self.data_folder or DEFAULT_DATA_FOLDER
        path = QFileDialog.getExistingDirectory(self, "Open PriVis Data Folder", str(start))
        if path:
            self.load_folder(path)

    def load_folder(self, folder):
        if self._load_thread is not None:
            return
        folder = Path(folder)
        self.load_error.hide()
        self.source_status.setText(f"Loading {folder.name}…")
        self.open_folder.setEnabled(False)
        worker = ReviewLoadThread(folder, self.review_date or date.today(), self)
        self._load_thread = worker
        worker.finished.connect(self._finish_load)
        worker.start()

    def _finish_load(self):
        worker = self._load_thread
        self._load_thread = None
        worker.deleteLater()
        if self._close_after_load:
            self.close()
            return
        self.open_folder.setEnabled(True)
        if worker.error is not None:
            status = "No dataset loaded"
            if self.data_folder is not None:
                status = f"Still showing {self.data_folder.name}"
            self.source_status.setText(status)
            self.load_error.setText(f"Could not open the data folder. {worker.error}")
            self.load_error.show()
            return

        review = worker.result
        self.data_folder = worker.folder
        self.simulations.set_data(review)
        self.advanced.set_data(review)
        self.overview.set_data(review)
        self.users.set_data(review.user_rows, review.user_detail)
        self.groups.set_data(review.group_rows, review.group_detail)
        self.findings.set_data(review.finding_rows, review.finding_detail)
        self.source_status.setText(f"{worker.folder.name} · Read only\nAs of {review.review_date}")
        self.source_status.setToolTip(str(worker.folder))

    def closeEvent(self, event):
        if self._load_thread is not None:
            self._close_after_load = True
            self.hide()
            event.ignore()
            return
        super().closeEvent(event)

    def _heading(self, text, name):
        label = QLabel(text)
        label.setObjectName(name)
        if self._heading_font is not None:
            label.setFont(self._heading_font)
        return label

    def _section_page(self, title, widget):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(18)
        layout.addWidget(self._heading("Access Overview" if title == "Overview" else title, "pageTitle"))
        layout.addWidget(widget, stretch=1)
        return page
