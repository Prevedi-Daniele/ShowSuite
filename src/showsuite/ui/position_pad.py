"""HUD Posizione stile Lightkey: pad XY pan/tilt con valori in gradi (range preso dal fixture)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PadWidget(QWidget):
    moved = Signal(float, float)       # pan, tilt normalizzati 0-1

    def __init__(self):
        super().__init__()
        self.pan = self.tilt = 0.5
        self.setMinimumSize(130, 130); self.setCursor(Qt.CrossCursor)

    def set_values(self, pan: float, tilt: float) -> None:
        self.pan, self.tilt = pan, tilt; self.update()

    def _from(self, pos: QPointF) -> None:
        r = self.rect().adjusted(6, 6, -6, -6)
        self.pan = min(1, max(0, (pos.x() - r.left()) / r.width()))
        self.tilt = min(1, max(0, (pos.y() - r.top()) / r.height()))
        self.moved.emit(self.pan, self.tilt); self.update()

    def mousePressEvent(self, e): self._from(e.position())
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._from(e.position())

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect().adjusted(6, 6, -6, -6))
        p.setPen(QPen(QColor(60, 64, 74))); p.setBrush(QColor(20, 21, 25)); p.drawRoundedRect(r, 6, 6)
        p.drawLine(QPointF(r.center().x(), r.top()), QPointF(r.center().x(), r.bottom()))
        p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))
        c = QPointF(r.left() + self.pan * r.width(), r.top() + self.tilt * r.height())
        p.setPen(QPen(QColor(58, 139, 255), 2)); p.setBrush(QColor(58, 139, 255, 120)); p.drawEllipse(c, 7, 7)


class PositionPad(QWidget):
    """Pad + due spinbox in gradi (0° = centro). `apply(pan, tilt)` riceve valori 0-1 (None = non toccare)."""

    def __init__(self, apply, pan_range: float = 540.0, tilt_range: float = 270.0):
        super().__init__()
        self.apply, self.ranges = apply, [pan_range, tilt_range]
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        self.pad = PadWidget(); lay.addWidget(self.pad, 1)
        row = QHBoxLayout(); lay.addLayout(row)
        self.spins = []
        for lab, rng in (("Pan", pan_range), ("Tilt", tilt_range)):
            s = QDoubleSpinBox(); s.setRange(-rng / 2, rng / 2); s.setSuffix("°"); s.setDecimals(1)
            row.addWidget(QLabel(lab)); row.addWidget(s); self.spins.append(s)
        self.pad.moved.connect(self._pad)
        self.spins[0].valueChanged.connect(lambda v: self._deg(0, v))
        self.spins[1].valueChanged.connect(lambda v: self._deg(1, v))

    def set_ranges(self, pan_range: float, tilt_range: float) -> None:
        self.ranges = [pan_range, tilt_range]
        for s, r in zip(self.spins, self.ranges):
            s.blockSignals(True); s.setRange(-r / 2, r / 2); s.blockSignals(False)

    def show_values(self, pan: float, tilt: float) -> None:
        """Mostra lo stato corrente (0-1) senza inviare nulla al motore."""
        self.pad.set_values(pan, tilt)
        for s, v, r in zip(self.spins, (pan, tilt), self.ranges):
            s.blockSignals(True); s.setValue((v - 0.5) * r); s.blockSignals(False)

    def _pad(self, pan: float, tilt: float) -> None:
        for s, v, r in zip(self.spins, (pan, tilt), self.ranges):
            s.blockSignals(True); s.setValue((v - 0.5) * r); s.blockSignals(False)
        self.apply(pan, tilt)

    def _deg(self, i: int, deg: float) -> None:
        v = deg / self.ranges[i] + 0.5
        self.pad.set_values(v if i == 0 else self.pad.pan, v if i == 1 else self.pad.tilt)
        self.apply(v if i == 0 else None, v if i == 1 else None)
