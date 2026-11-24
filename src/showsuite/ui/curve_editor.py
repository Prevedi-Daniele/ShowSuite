"""Editor di curve di fade: punti trascinabili (doppio clic = aggiungi, clic destro = rimuovi)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..light.live import interp_curve


class CurveWidget(QWidget):
    changed = Signal()

    def __init__(self, points=None, parent=None):
        super().__init__(parent)
        self.points: list[list[float]] = [list(p) for p in (points or [])]
        self.setMinimumSize(260, 260); self._drag = None

    def _r(self) -> QRectF:
        return QRectF(14, 14, self.width() - 28, self.height() - 28)

    def to_px(self, x, y) -> QPointF:
        r = self._r(); return QPointF(r.left() + x * r.width(), r.bottom() - y * r.height())

    def from_px(self, p) -> tuple[float, float]:
        r = self._r()
        return (max(0.0, min(1.0, (p.x() - r.left()) / r.width())), max(0.0, min(1.0, (r.bottom() - p.y()) / r.height())))

    def _hit(self, pos):
        for i, (x, y) in enumerate(self.points):
            if (self.to_px(x, y) - pos).manhattanLength() < 12:
                return i
        return None

    def mousePressEvent(self, e):
        i = self._hit(e.position())
        if e.button() == Qt.RightButton and i is not None:
            del self.points[i]; self.changed.emit(); self.update()
        elif e.button() == Qt.LeftButton:
            self._drag = i

    def mouseDoubleClickEvent(self, e):
        if self._hit(e.position()) is None:
            self.points.append(list(self.from_px(e.position()))); self.points.sort(); self.changed.emit(); self.update()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.points[self._drag] = list(self.from_px(e.position())); self.changed.emit(); self.update()

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self.points.sort(); self._drag = None; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1b1d23")); r = self._r()
        p.setPen(QPen(QColor("#3a3d46"), 1)); p.drawRect(r)
        p.setPen(QPen(QColor("#4da3ff"), 2))
        prev = self.to_px(0, 0)
        for i in range(1, 101):
            q = self.to_px(i / 100, interp_curve(self.points, i / 100)); p.drawLine(prev, q); prev = q
        p.setBrush(QColor("#fff"))
        for x, y in self.points:
            p.drawEllipse(self.to_px(x, y), 5, 5)


class CurveDialog(QDialog):
    def __init__(self, points, parent=None):
        super().__init__(parent); self.setWindowTitle("Curva di fade personalizzata")
        self.w = CurveWidget(points); lay = QVBoxLayout(self); lay.addWidget(self.w, 1)
        row = QHBoxLayout()
        reset = QPushButton("Azzera"); reset.clicked.connect(lambda: (self.w.points.clear(), self.w.update()))
        ok = QPushButton("Fatto"); ok.clicked.connect(self.accept)
        row.addWidget(reset); row.addStretch(); row.addWidget(ok); lay.addLayout(row)

    def points(self) -> list[tuple[float, float]]:
        return [tuple(p) for p in sorted(self.w.points)]
