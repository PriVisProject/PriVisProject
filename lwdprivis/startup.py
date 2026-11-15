"""Branded startup and local administrator sign-in."""

from hashlib import sha256
from hmac import compare_digest

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRegularExpression, QSize, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from visual_theme import icon


ADMIN_PASSWORD_DIGESTS = {
    "20262026": "ed0cff3ba737259c2e2e664412a10f9947dbcb1240b86d109f81fa4b3e7b358b",
    "12345678": "1092a2e7d101b98f876ab59e499b7120bcfc84ee171993bd7caaf34735144268",
}


STARTUP_STYLE = """
QDialog { background: #101C30; }
QLabel { color: #DCE4EE; }
QLabel#brandMark { background: #24364B; border-radius: 11px; }
QLabel#brand { font-size: 38px; font-weight: 700; }
QLabel#title { color: #F5F8FC; font-size: 22px; font-weight: 700; }
QLabel#hint { color: #B8C8DB; }
QLabel#error { color: #FFB1BD; }
QLineEdit {
    background: #F5F8FC; color: #101C30; border: 1px solid #627995;
    border-radius: 8px; padding: 8px 10px;
}
QLineEdit:focus { border-color: #55D6CB; }
QPushButton {
    color: #101C30; background: #17B8A6; border: 1px solid #17B8A6;
    border-radius: 8px; padding: 9px 16px; font-weight: 700;
}
QPushButton[workspaceChoice="true"], QPushButton#signIn { outline: none; }
QPushButton:hover { background: #55D6CB; }
QPushButton:focus { border-color: #F5F8FC; }
QProgressBar { background: #24364B; border: 0; border-radius: 5px; }
QProgressBar::chunk { background: #17B8A6; border-radius: 5px; }
"""


class StartupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.start_empty = False
        self.setWindowTitle("PriVis")
        self.setWindowIcon(icon("PriVis"))
        self.setMinimumWidth(460)
        self.setStyleSheet(STARTUP_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        panel = QWidget()
        panel.setFixedWidth(360)
        outer.addStretch()
        outer.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        mark = QLabel()
        mark.setObjectName("brandMark")
        mark.setFixedSize(46, 46)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setPixmap(icon("PriVis").pixmap(QSize(24, 24)))
        layout.addWidget(mark, alignment=Qt.AlignmentFlag.AlignHCenter)
        brand = QLabel('<span style="color:#F5F8FC">Pri</span><span style="color:#55D6CB">Vis</span>')
        brand.setObjectName("brand")
        tagline = QLabel("See the Access. Reduce the Risk.")
        tagline.setObjectName("hint")
        for label in (brand, tagline):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        loading = QWidget()
        loading_layout = QVBoxLayout(loading)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        loading_layout.addStretch()
        status = QLabel("Loading PriVis…")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        loading_layout.addWidget(self.progress)
        loading_layout.addStretch()
        self.loading = loading
        self.pages.addWidget(loading)

        self.mode = QWidget()
        mode_layout = QVBoxLayout(self.mode)
        mode_layout.setContentsMargins(0, 14, 0, 0)
        mode_layout.setSpacing(10)
        mode_title = QLabel("Choose a workspace")
        mode_title.setObjectName("title")
        mode_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_layout.addWidget(mode_title)
        self.demo_button = QPushButton("Demo Mode")
        self.demo_button.setAutoDefault(False)
        self.demo_button.setProperty("workspaceChoice", True)
        self.demo_button.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.demo_button.setToolTip("Start with the built-in sample dataset.")
        self.demo_button.clicked.connect(lambda: self.show_login(start_empty=False))
        mode_layout.addWidget(self.demo_button)
        self.import_button = QPushButton("New Import Mode")
        self.import_button.setAutoDefault(False)
        self.import_button.setProperty("workspaceChoice", True)
        self.import_button.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.import_button.setToolTip("Start with an empty workspace and import your CSV files.")
        self.import_button.clicked.connect(lambda: self.show_login(start_empty=True))
        mode_layout.addWidget(self.import_button)
        mode_layout.addStretch()
        self.pages.addWidget(self.mode)

        self.login = QWidget()
        login_layout = QVBoxLayout(self.login)
        login_layout.setContentsMargins(0, 14, 0, 0)
        login_layout.setSpacing(8)
        title = QLabel("Admin Sign In")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(title)
        fields = QFormLayout()
        fields.setVerticalSpacing(7)
        fields.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.user_id = QLineEdit()
        self.user_id.setMaxLength(8)
        self.user_id.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{8}"), self))
        self.user_id.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        fields.addRow("&User ID", self.user_id)
        fields.addRow("&Password", self.password)
        login_layout.addLayout(fields)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(self.error)
        submit = QPushButton("Sign In")
        submit.setObjectName("signIn")
        submit.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        submit.setDefault(True)
        submit.clicked.connect(self.validate_login)
        submit.setMinimumWidth(120)
        login_layout.addWidget(submit, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.pages.addWidget(self.login)

        self.animation = QPropertyAnimation(self.progress, b"value", self)
        self.animation.setDuration(1350)
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self.show_mode)

    def showEvent(self, event):
        super().showEvent(event)
        if self.pages.currentWidget() is self.loading:
            self.animation.start()

    def show_mode(self):
        self.pages.setCurrentWidget(self.mode)
        self.demo_button.setFocus()

    def show_login(self, *, start_empty):
        self.start_empty = start_empty
        self.user_id.clear()
        self.password.clear()
        self.error.clear()
        self.pages.setCurrentWidget(self.login)
        self.user_id.setFocus()

    def validate_login(self):
        if self.pages.currentWidget() is not self.login:
            return
        expected = ADMIN_PASSWORD_DIGESTS.get(self.user_id.text())
        entered = sha256(self.password.text().encode("utf-8")).hexdigest()
        if expected is None or not compare_digest(expected, entered):
            self.error.setText("Invalid User ID or Password")
            self.password.selectAll()
            self.password.setFocus()
            return
        self.password.clear()
        self.accept()
