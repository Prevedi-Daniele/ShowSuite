"""Editor effetti di posizione: griglia di figure, durata e offset (come in Lightkey)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from ..light.posfx import PATTERNS, POSITION_LIBRARY, PositionEffect, position_template


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


class PathPad(QWidget):
    """Disegno del movement path: clic = nuovo punto, trascina = sposta, tasto destro = elimina."""
    changed = Signal()

    def __init__(self, effect: PositionEffect):
        super().__init__()
        self.effect = effect; self.drag = None
        self.setMinimumSize(200, 200)

    def _to(self, x, y):
        r = min(self.width(), self.height()) / 2 - 8
        return QPointF(self.width() / 2 + x * r, self.height() / 2 + y * r)

    def _from(self, pos):
        r = min(self.width(), self.height()) / 2 - 8
        return (max(-1, min(1, (pos.x() - self.width() / 2) / r)), max(-1, min(1, (pos.y() - self.height() / 2) / r)))

    def _hit(self, pos):
        for i, q in enumerate(self.effect.path):
            d = self._to(*q) - pos
            if d.x() ** 2 + d.y() ** 2 <= 100:
                return i
        return None

    def mousePressEvent(self, e):
        i = self._hit(e.position())
        if e.button() == Qt.RightButton:
            if i is not None:
                del self.effect.path[i]
        elif i is not None:
            self.drag = i
        else:
            self.effect.path.append(self._from(e.position())); self.drag = len(self.effect.path) - 1
        self.update(); self.changed.emit()

    def mouseMoveEvent(self, e):
        if self.drag is not None and self.drag < len(self.effect.path):
            self.effect.path[self.drag] = self._from(e.position()); self.update(); self.changed.emit()

    def mouseReleaseEvent(self, _):
        self.drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(20, 21, 25))
        p.setPen(QPen(QColor(60, 64, 74)))
        c = self._to(0, 0); r = min(self.width(), self.height()) / 2 - 8
        p.drawEllipse(c, r, r); p.drawLine(QPointF(c.x() - r, c.y()), QPointF(c.x() + r, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - r), QPointF(c.x(), c.y() + r))
        pts = [tuple(q) for q in self.effect.path]
        if len(pts) >= 2:
            fx = PositionEffect("Path", 1.0, 0.0, path=pts, smooth=self.effect.smooth)
            path = QPainterPath()
            for i in range(121):
                x, y = fx.point(i / 120); pt = self._to(x, y)
                path.moveTo(pt) if i == 0 else path.lineTo(pt)
            p.setPen(QPen(QColor("#5fe3d0"), 1.6)); p.drawPath(path)
        p.setPen(QPen(QColor("#3a8bff"), 2)); p.setBrush(QColor("#3a8bff"))
        for q in pts:
            p.drawEllipse(self._to(*q), 4, 4)


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
        self.tpl = QComboBox(); self.tpl.addItem("Template…"); self.tpl.addItems(list(POSITION_LIBRARY))
        self.tpl.activated.connect(self._template)
        self.rev = QCheckBox("Direzione inversa"); self.rev.setChecked(self.effect.reverse); self.rev.toggled.connect(self._params)
        self.smooth = QCheckBox("Percorso morbido"); self.smooth.setChecked(self.effect.smooth); self.smooth.toggled.connect(self._params)
        self.pad = PathPad(self.effect); self.pad.changed.connect(lambda: self.changed.emit(self.effect))
        side.addWidget(self.tpl); side.addWidget(self.rev); side.addWidget(self.smooth); side.addWidget(self.pad)
        side.addStretch()
        lay = QHBoxLayout(self); lay.addLayout(grid, 1); lay.addLayout(side)
        self.pick(self.effect.pattern, emit=False)

    def _template(self, i: int):
        if i <= 0:
            return
        t = position_template(self.tpl.currentText())
        for k in ("pattern", "duration", "time_offset", "size", "path", "smooth", "reverse"):
            setattr(self.effect, k, getattr(t, k))
        self.dur.blockSignals(True); self.dur.setValue(t.duration); self.dur.blockSignals(False)
        self.toff.blockSignals(True); self.toff.setValue(round(t.time_offset * 100)); self.toff.blockSignals(False)
        self.pick(self.effect.pattern)

    def pick(self, name: str, emit: bool = True):
        self.effect.pattern = name
        self.pad.setVisible(name == "Path"); self.pad.update()
        for n, b in self.icons.items():
            b.setChecked(n == name)
        if emit:
            self.changed.emit(self.effect)

    def _params(self, *_):
        e = self.effect
        e.duration, e.time_offset = self.dur.value(), self.toff.value() / 100
        e.pan_offset, e.tilt_offset = self.poff.value(), self.tioff.value()
        e.reverse, e.smooth = self.rev.isChecked(), self.smooth.isChecked(); self.pad.update()
        self.changed.emit(e)
