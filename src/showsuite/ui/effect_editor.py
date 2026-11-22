"""Editor effetti di posizione: griglia di figure, durata e offset (come in Lightkey)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from ..light.posfx import PATTERNS, PositionEffect


class PatternIcon(QPushButton):
    def __init__(self, name: str, size: int = 92):
        super().__init__()
        self.name = name
        self.setCheckable(True); self.setFixedSize(size + 12, size + 34)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding-top:92px;font-size:11px;} QPushButton:checked{background:#3a8b6a;border-radius:8px;}")
        self.setText(name); self.setToolTip(name)
        self._sz = size

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, 6 + self._sz / 2); r = self._sz / 2
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        for k in (1, 0.66, 0.33):
            p.drawEllipse(c, r * k, r * k)
        p.setPen(QPen(QColor("#5fe3d0"), 1.6))
        fx = PositionEffect(self.name, 1.0, 0.0)
        path = QPainterPath()
        n = 24 if self.name == "Random Dots" else 120
        for i in range(n + 1):
            x, y = fx.point(i / n if self.name != "Random Dots" else i / 8 + 0.01)
            pt = QPointF(c.x() + x * r * 0.9, c.y() + y * r * 0.9)
            if self.name == "Random Dots":
                p.drawPoint(pt)
            elif i == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        if self.name != "Random Dots":
            p.drawPath(path)


class PositionEffectEditor(QWidget):
    changed = Signal(object)

    def __init__(self, effect: PositionEffect | None = None):
        super().__init__()
        self.effect = effect or PositionEffect()
        grid = QGridLayout(); self.icons: dict[str, PatternIcon] = {}
        for i, name in enumerate(PATTERNS):
            b = PatternIcon(name); b.clicked.connect(lambda _=0, n=name: self.pick(n))
            self.icons[name] = b; grid.addWidget(b, i // 7, i % 7)
        self.dur = QDoubleSpinBox(); self.dur.setRange(0.1, 600); self.dur.setSuffix(" s"); self.dur.setValue(self.effect.duration)
        self.toff = QSpinBox(); self.toff.setRange(0, 100); self.toff.setSuffix(" %"); self.toff.setValue(round(self.effect.time_offset * 100))
        self.poff = QDoubleSpinBox(); self.poff.setRange(-180, 180); self.poff.setSuffix("°")
        self.tioff = QDoubleSpinBox(); self.tioff.setRange(-180, 180); self.tioff.setSuffix("°")
        for w in (self.dur, self.toff, self.poff, self.tioff):
            (w.valueChanged).connect(self._params)
        side = QVBoxLayout()
        for lab, w in (("Duration", self.dur), ("Time Offset", self.toff), ("Pan Offset", self.poff), ("Tilt Offset", self.tioff)):
            side.addWidget(QLabel(lab)); side.addWidget(w)
        side.addStretch()
        lay = QHBoxLayout(self); lay.addLayout(grid, 1); lay.addLayout(side)
        self.pick(self.effect.pattern, emit=False)

    def pick(self, name: str, emit: bool = True):
        self.effect.pattern = name
        for n, b in self.icons.items():
            b.setChecked(n == name)
        if emit:
            self.changed.emit(self.effect)

    def _params(self, *_):
        e = self.effect
        e.duration, e.time_offset = self.dur.value(), self.toff.value() / 100
        e.pan_offset, e.tilt_offset = self.poff.value(), self.tioff.value()
        self.changed.emit(e)
