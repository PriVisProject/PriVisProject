"""Remediation playbook scoped to the Advanced sandbox."""

from html import escape

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from review_pages import ReviewTable, detail_section
from solutions import remedy
from visual_theme import SEVERITY


class SolutionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.review = None
        self.remaining = []
        layout = QVBoxLayout(self)
        note = QLabel(
            "Actions apply to an in-memory sandbox. Reimport the dataset to reset it."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.results = QLabel()
        self.results.setWordWrap(True)
        layout.addWidget(self.results)
        self.actions = ReviewTable(
            ("Severity", "Account", "Department", "Sandbox action"),
            0, "All severities", SEVERITY,
        )
        layout.addWidget(self.actions, 1)

        buttons = QHBoxLayout()
        self.highlighted = QPushButton("Execute Highlighted Fix")
        self.highlighted.setProperty("solutionAction", True)
        self.all_fixes = QPushButton("Execute All Fixes")
        self.all_fixes.setProperty("solutionAction", True)
        buttons.addWidget(self.highlighted)
        buttons.addWidget(self.all_fixes)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.highlighted.clicked.connect(self.execute_highlighted)
        self.all_fixes.clicked.connect(self.execute_all)
        self.actions.table.selectionModel().currentChanged.connect(self.update_buttons)
        self.actions.search.textChanged.connect(self.update_buttons)
        self.actions.category.currentIndexChanged.connect(self.update_buttons)
        self.update_buttons()

    def set_data(self, review):
        self.review = review
        self.dataset = review.dataset
        self.remaining = review.findings
        self.results.setText(f"{len(self.remaining)} findings in the sandbox.")
        self.refresh()

    def refresh(self):
        rows = [
            (
                f.severity, f.account_name, self.review.users_by_id[f.user_id].department,
                f"Remove {f.group_name}" if f.group_id is not None else "Disable account",
            )
            for f in self.remaining
        ]
        self.actions.set_data(rows, self.detail)
        self.update_buttons()

    def detail(self, index):
        f = self.remaining[index]
        heading = escape(f"{f.user_name} ({f.account_name}, {f.user_id})")
        action = f"Remove direct membership in {f.group_name}." if f.group_id else "Disable the account."
        return (
            f"<p><b>{heading}</b></p>"
            + detail_section("Sandbox Action", [action])
            + detail_section("Review Recommendation", [f.recommendation])
        )

    def update_buttons(self):
        self.highlighted.setEnabled(self.actions.table.currentIndex().isValid())
        self.all_fixes.setEnabled(bool(self.remaining))

    def execute_highlighted(self):
        index = self.actions.proxy.mapToSource(self.actions.table.currentIndex())
        if index.isValid():
            self.execute([self.remaining[index.row()]])

    def execute_all(self):
        if self.remaining:
            self.execute(self.remaining)

    def execute(self, fixes):
        before = len(self.remaining)
        self.dataset, self.remaining = remedy(self.dataset, fixes, self.review.review_date)
        self.results.setText(
            f"Executed {len(fixes)} sandbox action(s). Findings: {before} before → "
            f"{len(self.remaining)} after."
        )
        self.refresh()
