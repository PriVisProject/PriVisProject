"""Read-only Qt widgets for reviewing a validated dataset."""

from collections import Counter, defaultdict
from datetime import date
from html import escape

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRectF, QSortFilterProxyModel, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QSplitter, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableView, QTextEdit, QVBoxLayout, QWidget,
)

from access_evidence import collect_evidence
from data_loader import Dataset, load_dataset
from security_analysis import analyze_findings
from visual_theme import PriVisComboBox, SEVERITY


RISK_COLORS = {severity: colors[2] for severity, colors in SEVERITY.items()}
RULE_NAMES = {
    "expired_account": "Expired enabled account",
    "denied_membership": "Denied membership",
    "approval_required": "Approval required",
}


def detail_lines(lines):
    """Render imported values as literal text within a detail section."""
    return "<br>".join(escape(line) for line in lines)


def detail_section(heading, lines):
    return f"<p><b>{escape(heading)}:</b><br>{detail_lines(lines or ['None'])}</p>"


class ReviewData:
    """Prepare rows and detail indexes without accessing Qt widgets."""

    def __init__(self, dataset: Dataset, review_date: date):
        self.dataset = dataset
        self.review_date = review_date
        self.findings = analyze_findings(dataset, review_date=review_date)
        self.users = list(dataset.users.itertuples(index=False))
        self.groups = list(dataset.groups.itertuples(index=False))
        self.user_rows = [
            (u.name, u.sam_account_name, u.department, u.role, u.worker_type,
             "Enabled" if u.enabled else "Disabled")
            for u in self.users
        ]
        self.group_rows = [(g.group_name, g.description, g.risk_level) for g in self.groups]
        self.finding_rows = [
            (f.severity, f.user_name, f.group_name or "—", RULE_NAMES[f.rule])
            for f in self.findings
        ]
        self.groups_by_id = {g.group_id: g for g in self.groups}
        self.users_by_id = {u.user_id: u for u in self.users}
        self.memberships_by_user = defaultdict(list)
        self.memberships_by_group = defaultdict(list)
        self.findings_by_user = defaultdict(list)
        for membership in dataset.memberships.itertuples(index=False):
            self.memberships_by_user[membership.user_id].append(membership)
            self.memberships_by_group[membership.group_id].append(membership)
        for finding in self.findings:
            self.findings_by_user[finding.user_id].append(finding)
        self.membership_evidence = collect_evidence(self)

    def user_detail(self, index):
        user = self.users[index]
        memberships = self.memberships_by_user.get(user.user_id, ())
        findings = self.findings_by_user.get(user.user_id, ())
        groups = [
            f"{self.groups_by_id[m.group_id].group_name} ({m.group_id}) · {m.approval_status}"
            for m in memberships
        ]
        issues = []
        for finding in findings:
            issues.extend((
                f"{finding.severity} · {RULE_NAMES[finding.rule]} · {finding.group_name or 'Account'}",
                finding.explanation,
            ))
        title = escape(f"{user.name} ({user.user_id})")
        return (
            f"<p><b>{title}</b><br><b>End date:</b> {user.end_date or '—'}</p>"
            + detail_section(f"Direct group memberships ({len(groups)})", groups)
            + detail_section(f"Findings ({len(findings)})", issues)
        )

    def group_detail(self, index):
        group = self.groups[index]
        members = [
            self.users_by_id[m.user_id]
            for m in self.memberships_by_group.get(group.group_id, ())
        ]
        rows = [
            f"{u.name} ({u.sam_account_name}) · {'Enabled' if u.enabled else 'Disabled'}"
            for u in members
        ]
        title = escape(f"{group.group_name} ({group.group_id}) · {group.risk_level} risk")
        return (
            f"<p><b>{title}</b><br>{escape(group.description)}"
            f"<br><b>Resource scope:</b> {escape(group.resource_scope)}</p>"
            + detail_section(f"Direct members ({len(rows)})", rows)
        )

    def finding_detail(self, index):
        finding = self.findings[index]
        policy = "Account end-date rule"
        if finding.policy_decision:
            policy = f"{finding.role} / {finding.group_id} / {finding.policy_decision}\n"
            policy += finding.policy_reason
        title = escape(f"{finding.severity} · {RULE_NAMES[finding.rule]}")
        account = escape(f"{finding.user_name} ({finding.account_name}, {finding.user_id})")
        group = escape(finding.group_name or "—")
        return (
            f"<p><b>{title}</b><br>"
            f"<b>Account:</b> {account}<br><b>Group:</b> {group}</p>"
            + detail_section("Matching Rule", policy.splitlines())
            + detail_section("Explanation", [finding.explanation])
            + detail_section("Review Recommendation", [finding.recommendation])
        )


def load_review(folder, review_date):
    return ReviewData(load_dataset(folder), review_date)


class ReviewTableModel(QAbstractTableModel):
    def __init__(self, headers, parent):
        super().__init__(parent)
        self.headers = headers
        self.rows = []
        self.cell_colors = None

    def replace_rows(self, rows, cell_colors=None):
        self.beginResetModel()
        self.rows = rows
        self.cell_colors = cell_colors
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.BackgroundRole and self.cell_colors is not None:
            color = self.cell_colors(index.row(), index.column())
            return QColor(color) if color else None
        if role == Qt.ItemDataRole.FontRole and self.headers[index.column()] == "Account ID":
            if "JetBrains Mono" in QFontDatabase.families():
                return QFont("JetBrains Mono")
            return QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return self.rows[index.row()][index.column()]
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return super().headerData(section, orientation, role)


class ReviewFilter(QSortFilterProxyModel):
    def __init__(self, filter_column, parent):
        super().__init__(parent)
        self.filter_column = filter_column
        self.search_text = ""
        self.category = None

    def update_filter(self, search, category):
        self.beginFilterChange()
        self.search_text = search.strip().casefold()
        self.category = category
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row, source_parent):
        row = self.sourceModel().rows[source_row]
        return (self.category is None or row[self.filter_column] == self.category) and (
            not self.search_text or any(self.search_text in value.casefold() for value in row)
        )


class ReviewCellDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # The view paints the row outline. Keep each cell's normal background.
        option.state &= ~(QStyle.StateFlag.State_HasFocus | QStyle.StateFlag.State_Selected)
        if option.backgroundBrush.style() == Qt.BrushStyle.NoBrush:
            color = "#F5F8FC" if index.row() % 2 else "#FFFFFF"
            option.backgroundBrush = QBrush(QColor(color))


class SeverityDelegate(ReviewCellDelegate):
    def paint(self, painter, option, index):
        label = index.data()
        if label not in SEVERITY:
            super().paint(painter, option, index)
            return
        background, foreground, _ = SEVERITY[label]
        base = QStyleOptionViewItem(option)
        self.initStyleOption(base, index)
        base.text = ""
        option.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, base, painter, option.widget)
        width = min(option.fontMetrics.horizontalAdvance(label) + 30, option.rect.width() - 12)
        pill = QRectF(option.rect.x() + 6, option.rect.center().y() - 11, width, 23)
        painter.save()
        painter.setClipRect(option.rect)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(pill, 7, 7)
        painter.setBrush(QColor(foreground))
        painter.drawEllipse(QRectF(pill.x() + 8, pill.center().y() - 3, 6, 6))
        painter.setPen(QColor(foreground))
        painter.drawText(pill.adjusted(19, 0, -3, 0), Qt.AlignmentFlag.AlignVCenter, label)
        painter.restore()


class ReviewTableView(QTableView):
    def paintEvent(self, event):
        super().paintEvent(event)
        selected = self.selectionModel().selectedRows()
        if not selected:
            return

        row = selected[0].row()
        header = self.horizontalHeader()
        left = max(0, -header.offset())
        right = min(self.viewport().width(), header.length() - header.offset())
        bounds = QRectF(
            left, self.rowViewportPosition(row), right - left, self.rowHeight(row),
        )
        with QPainter(self.viewport()) as painter:
            painter.setClipRegion(event.region())
            painter.setPen(QPen(QColor("#15396F"), 2))
            painter.drawRect(bounds.adjusted(1, 1, -1, -1))


class ReviewTable(QWidget):
    def __init__(self, headers, filter_column, all_label, categories):
        super().__init__()
        self.detail_for_row = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search table")
        self.search.setAccessibleName("Search table")
        self.search.setClearButtonEnabled(True)
        self.category = PriVisComboBox()
        self.category.setAccessibleName(all_label)
        self.category.addItem(all_label, None)
        for category in categories:
            self.category.addItem(category, category)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.category)
        layout.addLayout(filters)

        self.count = QLabel("No data loaded")
        self.count.setObjectName("rowCount")
        layout.addWidget(self.count)
        split = QSplitter(Qt.Orientation.Vertical)
        self.model = ReviewTableModel(headers, self)
        self.proxy = ReviewFilter(filter_column, self)
        self.proxy.setSourceModel(self.model)
        self.table = ReviewTableView()
        self.table.setItemDelegate(ReviewCellDelegate(self.table))
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setShowGrid(False)
        if filter_column in (0, 2):
            self.table.setItemDelegateForColumn(filter_column, SeverityDelegate(self.table))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        split.addWidget(self.table)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setAccessibleName("Selected row details")
        split.addWidget(self.detail)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        self.search.textChanged.connect(self.apply_filters)
        self.category.currentIndexChanged.connect(self.apply_filters)
        self.table.selectionModel().currentChanged.connect(self.show_detail)

    def set_data(self, rows, detail_for_row, *, cell_colors=None):
        self.detail_for_row = detail_for_row
        self.model.replace_rows(rows, cell_colors)
        self.apply_filters()

    def apply_filters(self):
        self.proxy.update_filter(self.search.text(), self.category.currentData())
        visible = self.proxy.rowCount()
        self.count.setText(f"{visible} of {self.model.rowCount()} rows")
        if visible and not self.table.currentIndex().isValid():
            self.table.selectRow(0)
        self.show_detail(self.table.currentIndex())

    def show_detail(self, current):
        if current.isValid() and self.detail_for_row is not None:
            row = self.proxy.mapToSource(current).row()
            self.detail.setHtml(self.detail_for_row(row))
        else:
            self.detail.setPlainText("No matching rows.")


class RiskBar(QWidget):
    def __init__(self):
        super().__init__()
        self.counts = Counter()
        self.setFixedHeight(15)

    def paintEvent(self, event):
        bounds = QRectF(self.rect())
        outline = QPainterPath()
        outline.addRoundedRect(bounds, 7.5, 7.5)
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setClipPath(outline)
            total = sum(self.counts.values())
            if not total:
                painter.fillRect(bounds, QColor("#EAF0F7"))
                return
            offset = 0.0
            for severity, color in RISK_COLORS.items():
                width = bounds.width() * self.counts[severity] / total
                if width:
                    painter.fillRect(QRectF(offset, 0, width, bounds.height()), QColor(color))
                    if offset:
                        painter.fillRect(QRectF(offset, 0, min(2.0, width), bounds.height()), QColor("white"))
                    offset += width


class Overview(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        cards = QGridLayout()
        cards.setSpacing(12)
        self.metrics = []
        specs = (("Total users", 0, 0), ("Groups", 1, 0),
                 ("Risk findings", 0, 1), ("High priority", 1, 1))
        for label, row, col in specs:
            card, column = self.card()
            caption = QLabel(label)
            caption.setObjectName("metricCaption")
            column.addWidget(caption)
            number = QLabel("—")
            number.setObjectName("metricValue")
            if "Space Grotesk" in QFontDatabase.families():
                number.setFont(QFont("Space Grotesk"))
            column.addWidget(number)
            cards.addWidget(card, row, col)
            self.metrics.append(number)
        for col in (0, 1):
            cards.setColumnStretch(col, 1)
        layout.addLayout(cards)

        card, risk = self.card("Risk Distribution")
        self.risk_bar = RiskBar()
        risk.addWidget(self.risk_bar)
        legend = QGridLayout()
        self.legend = {}
        for index, severity in enumerate(SEVERITY):
            label = QLabel()
            label.setObjectName("metricCaption")
            self.legend[severity] = label
            legend.addWidget(label, index // 2, index % 2)
        risk.addLayout(legend)
        layout.addWidget(card)

        card, summary = self.card("Findings by Rule")
        self.summary = QLabel("Load a dataset to see findings.")
        self.summary.setWordWrap(True)
        self.summary.setMinimumHeight(self.summary.fontMetrics().lineSpacing() * 3 + 4)
        summary.addWidget(self.summary)
        layout.addWidget(card)
        layout.addStretch()

    @staticmethod
    def card(title=None):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 11, 16, 12)
        layout.setSpacing(6)
        if title:
            heading = QLabel(title)
            heading.setObjectName("sectionTitle")
            layout.addWidget(heading)
        return card, layout

    def set_data(self, data):
        counts = Counter(f.severity for f in data.findings)
        for label, value in zip(self.metrics, (
            len(data.users), len(data.groups), len(data.findings), counts["Critical"] + counts["High"],
        )):
            label.setText(str(value))
        self.risk_bar.counts = counts
        self.risk_bar.update()
        for severity, label in self.legend.items():
            label.setText(f"{severity} · {counts[severity]}")
        rules = Counter(f.rule for f in data.findings)
        self.summary.setText("\n".join(f"{name}: {rules[key]}" for key, name in RULE_NAMES.items()))
