"""PriVis palette and small Qt-rendered identity graphics."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox


SEVERITY = {
    "Critical": ("#FBE7EC", "#A91E45", "#DC5367"),
    "High": ("#FCEBEC", "#A52F43", "#C64456"),
    "Medium": ("#FFF3DC", "#85530B", "#D99928"),
    "Low": ("#E3F4F8", "#166178", "#16A37C"),
}


def icon(name, color="#55D6CB"):
    """Draw crisp line icons at the same scale as the sidebar text."""
    image = QPixmap(48, 48)
    image.setDevicePixelRatio(2)
    image.fill(Qt.GlobalColor.transparent)
    with QPainter(image) as painter:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.65)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        if name == "Overview":
            for x in (4, 13):
                for y in (4, 13):
                    painter.drawRoundedRect(QRectF(x, y, 7, 7), 1, 1)
        elif name == "Users":
            for x, y in ((8, 8), (16, 9)):
                painter.drawEllipse(QRectF(x - 2.5, y - 2.5, 5, 5))
                painter.drawArc(QRectF(x - 4.5, y + 4, 9, 9), 0, 180 * 16)
        elif name == "Groups":
            painter.drawLine(12, 8, 12, 12)
            painter.drawLine(6, 12, 18, 12)
            for x, y in ((12, 6), (6, 17), (18, 17)):
                painter.drawEllipse(QRectF(x - 2, y - 2, 4, 4))
            for x in (6, 18):
                painter.drawLine(x, 12, x, 15)
        elif name == "Findings":
            path = QPainterPath()
            path.moveTo(12, 3)
            path.lineTo(20, 6)
            path.cubicTo(20, 15, 18, 18, 12, 21)
            path.cubicTo(6, 18, 4, 15, 4, 6)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(12, 8, 12, 12)
            painter.drawPoint(12, 16)
        elif name == "Advanced":
            painter.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
            for y in (8, 12, 16):
                painter.drawPoint(8, y)
                painter.drawLine(11, y, 16, y)
        elif name == "Simulations":
            for y, x in ((6, 9), (12, 15), (18, 10)):
                painter.drawLine(4, y, x - 2, y)
                painter.drawLine(x + 2, y, 20, y)
                painter.drawLine(x, y - 2, x, y + 2)
        else:
            path = QPainterPath()
            path.moveTo(5, 12)
            path.quadTo(12, 3, 19, 12)
            path.quadTo(12, 21, 5, 12)
            painter.drawPath(path)
            painter.drawEllipse(QRectF(10, 10, 4, 4))
            for x, dx in ((3, 4), (21, -4)):
                for y, dy in ((3, 4), (21, -4)):
                    painter.drawLine(x, y, x + dx, y)
                    painter.drawLine(x, y, x, y + dy)
    return QIcon(image)


class PriVisComboBox(QComboBox):
    """Keep the native combo behavior with a palette-matched chevron."""

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        arrow = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option,
            QStyle.SubControl.SC_ComboBoxArrow, self,
        )
        center = QPointF(arrow.center())
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = "#24364B" if self.isEnabled() else "#627995"
            pen = QPen(QColor(color), 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            chevron = QPainterPath(center + QPointF(-4, -2))
            chevron.lineTo(center + QPointF(0, 2))
            chevron.lineTo(center + QPointF(4, -2))
            painter.drawPath(chevron)
