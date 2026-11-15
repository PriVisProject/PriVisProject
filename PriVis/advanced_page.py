"""Read-only access evidence and policy coverage for the active dataset."""

from html import escape

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from access_evidence import NO_POLICY, POLICY_DECISIONS
from review_pages import RULE_NAMES, ReviewTable, detail_section
from solutions_page import SolutionsPage
from visual_theme import SEVERITY


DEPARTMENT_COLORS = {
    "Customer Support": "#D4F5EE",
    "Finance": "#DDF2E0",
    "HR": "#D9F5FA",
    "IT": "#EDE2FA",
    "Sales": "#FFF0C8",
}
OTHER_DEPARTMENT = "#EAF0F7"


def legend_text(title, pairs):
    chips = " &nbsp; ".join(
        f'<span style="background-color:{color}; color:#24364B;"> &nbsp;{escape(label)}&nbsp; </span>'
        for label, color in pairs
    )
    return f"<b>{title}:</b> &nbsp;{chips}"


class AdvancedPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        intro = QLabel("Inspect direct memberships, group risk colors, and policy evidence.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.department_legend = QLabel()
        self.department_legend.setWordWrap(True)
        layout.addWidget(self.department_legend)
        self.alert_legend = QLabel(legend_text(
            "Alert colors", [(level, colors[0]) for level, colors in SEVERITY.items()],
        ))
        self.alert_legend.setWordWrap(True)
        layout.addWidget(self.alert_legend)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        headers = ("User", "Account ID", "Department", "Role", "Group", "Policy")
        self.evidence = ReviewTable(headers, 5, "All policy decisions", POLICY_DECISIONS)
        self.evidence.search.setPlaceholderText("Search users, accounts, departments, roles, or groups")
        tabs.addTab(self.evidence, "Access Evidence")

        coverage = QWidget()
        coverage_layout = QVBoxLayout(coverage)
        self.coverage_summary = QLabel("Load a dataset to review policy coverage.")
        self.coverage_summary.setWordWrap(True)
        coverage_layout.addWidget(self.coverage_summary)
        self.gaps = ReviewTable(headers, 5, "No matching policy", ())
        self.gaps.category.hide()
        coverage_layout.addWidget(self.gaps, 1)
        tabs.addTab(coverage, "Policy Coverage")
        self.solutions = SolutionsPage()
        tabs.addTab(self.solutions, "Solutions")

    def set_data(self, review):
        departments = {user.department for user in review.users}
        colors = [(name, color) for name, color in DEPARTMENT_COLORS.items() if name in departments]
        if departments.difference(DEPARTMENT_COLORS):
            colors.append(("Other departments", OTHER_DEPARTMENT))
        self.department_legend.setText(legend_text("Department colors", colors) if colors else "")
        self.solutions.set_data(review)
        evidence = review.membership_evidence
        gaps = [entry for entry in evidence if entry.policy is None]
        explanation = "Review the unmatched memberships below." if gaps else "No policy gaps found."
        self.coverage_summary.setText(
            f"{len(evidence) - len(gaps)} of {len(evidence)} direct memberships have a matching "
            f"role/group policy. {explanation}"
        )
        self.set_table(self.evidence, evidence, review.review_date)
        self.set_table(self.gaps, gaps, review.review_date)

    @staticmethod
    def set_table(table, entries, review_date):
        def cell_color(row, column):
            entry = entries[row]
            if column == 2:
                return DEPARTMENT_COLORS.get(entry.user.department, OTHER_DEPARTMENT)
            if column == 4:
                return SEVERITY[entry.group.risk_level][0]
            return None

        table.set_data(
            [entry.row for entry in entries],
            lambda index: evidence_detail(entries[index], review_date),
            cell_colors=cell_color,
        )


def evidence_detail(entry, review_date):
    user, group, membership = entry.user, entry.group, entry.membership
    account = escape(f"{user.name} ({user.sam_account_name}, {user.user_id})")
    group_name = escape(f"{group.group_name} ({group.group_id}) · {group.risk_level} risk")
    status = "Enabled" if user.enabled else "Disabled"
    policy_lines = [NO_POLICY, "No explicit decision exists for this role and group."]
    if entry.policy is not None:
        policy_lines = [
            f"{entry.policy.role} / {entry.policy.group_id} / {entry.policy.access_decision}",
            entry.policy.policy_reason,
        ]
    finding_lines = [
        f"{finding.severity} · {RULE_NAMES[finding.rule]}: {finding.explanation}"
        for finding in entry.findings
    ]
    if not finding_lines:
        finding_lines = [
            "No finding linked to this membership."
            if user.enabled else "PriVis skips disabled accounts in the findings review."
        ]
    return (
        f"<p><b>{account}</b><br>{escape(user.department)} · {escape(user.role)} · {status}"
        f"<br><b>Group:</b> {group_name}"
        f"<br><b>Resource scope:</b> {escape(group.resource_scope)}</p>"
        + detail_section("Matching Policy", policy_lines)
        + detail_section("Approval Evidence", [
            f"Status: {membership.approval_status}",
            f"Ticket: {membership.approval_ticket or '—'}",
            f"Expiry: {membership.approval_expires or '—'}",
        ])
        + detail_section(f"Membership Findings as of {review_date}", finding_lines)
    )
