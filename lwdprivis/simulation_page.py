"""Qt controls for an in-memory membership removal preview."""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from review_pages import RULE_NAMES, detail_section
from simulation import preview_removal
from visual_theme import PriVisComboBox


class SimulationPage(QWidget):
    def __init__(self):
        super().__init__()
        self.review = None
        self.baseline = ()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        note = QLabel("Check which findings would clear or remain if you removed a user from one group. This preview leaves source records untouched.")
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QFormLayout()
        self.user = PriVisComboBox()
        self.membership = PriVisComboBox()
        form.addRow("&User", self.user)
        form.addRow("&Membership", self.membership)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.preview_button = QPushButton("Preview Removal")
        self.preview_button.setObjectName("previewRemoval")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("resetSimulation")
        actions.addWidget(self.preview_button)
        actions.addWidget(self.reset_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.summary = QLabel()
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setAccessibleName("Simulation results")
        layout.addWidget(self.details, 1)

        self.user.currentIndexChanged.connect(self.update_memberships)
        self.membership.currentIndexChanged.connect(self.clear_preview)
        self.preview_button.clicked.connect(self.show_preview)
        self.reset_button.clicked.connect(self.reset)
        self.reset()

    def set_data(self, review):
        self.review = review
        self.baseline = tuple(review.findings)
        self.user.blockSignals(True)
        self.user.clear()
        self.user.addItem("Select a user")
        for user in review.users:
            self.user.addItem(f"{user.name} ({user.sam_account_name})", user.user_id)
        self.user.blockSignals(False)
        self.reset()

    def reset(self):
        self.user.setCurrentIndex(0)
        self.update_memberships()

    def update_memberships(self):
        user_id = self.user.currentData()
        self.membership.blockSignals(True)
        self.membership.clear()
        if user_id is not None:
            memberships = self.review.memberships_by_user.get(user_id, ())
            self.membership.addItem("Select a membership" if memberships else "No direct memberships")
            for membership in memberships:
                group = self.review.groups_by_id[membership.group_id]
                self.membership.addItem(f"{group.group_name} ({group.group_id})", group.group_id)
        else:
            self.membership.addItem("Select a user first")
        self.membership.setEnabled(self.membership.count() > 1)
        self.membership.blockSignals(False)
        self.clear_preview()

    def clear_preview(self):
        self.user.setEnabled(self.user.count() > 1)
        self.preview_button.setEnabled(self.membership.currentData() is not None)
        self.reset_button.setEnabled(self.user.currentData() is not None)
        self.details.clear()
        if self.review is None:
            self.summary.setText("Load a dataset to preview a change.")
        else:
            self.summary.setText(f"Baseline: {len(self.baseline)} findings as of {self.review.review_date}")

    def show_preview(self):
        user_id = self.user.currentData()
        group_id = self.membership.currentData()
        if user_id is None or group_id is None:
            return
        result = preview_removal(
            self.review.dataset, user_id=user_id, group_id=group_id,
            review_date=self.review.review_date, baseline=self.baseline,
        )
        self.summary.setText(
            f"All findings: {len(result.before)} before → {len(result.after)} after"
            f" · {len(result.cleared)} cleared · {len(result.added)} added"
        )
        account_before = [f for f in result.before if f.user_id == user_id]
        account_after = [f for f in result.after if f.user_id == user_id]
        sections = (
            ("Selected account before", account_before),
            ("Selected account after", account_after),
            ("Cleared findings", result.cleared),
            ("Added findings", result.added),
        )
        membership_name = escape(self.membership.currentText())
        paragraphs = [f"<p><b>Preview removal:</b> {membership_name}</p>"]
        for heading, findings in sections:
            lines = [
                f"{finding.severity} · {RULE_NAMES[finding.rule]} · "
                f"{finding.group_name or 'Account'}"
                for finding in findings
            ]
            paragraphs.append(detail_section(f"{heading} ({len(findings)})", lines))
        self.details.setHtml("".join(paragraphs))
