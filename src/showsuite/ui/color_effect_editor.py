"""Editor effetto colore: swatch o curve Hue/Saturation/Brightness trascinabili."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QColorDialog, QDoubleSpinBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget)

from ..light.colorfx import ColorEffect, curve_value

CHANNELS = (("hue", "Hue", "#5fe3d0"), ("saturation", "Saturation", "#ff6a5a"), ("brightness", "Brightness", "#ffd84a"))


class CurveEdit(QWidget):
    """Punti (x,y in 0-1) trascinabili; doppio clic aggiunge, clic destro rimuove."""
    changed = Signal()

    def __init__(self, effect: ColorEffect):
        super().__init__()
        self.effect, self.key, self.drag = effect, "hue", None
        self.setMinimumHeight(180); self.setMouseTracking(True)

    @property
    def pts(self) -> list[tuple[float, float]]:
        return getattr(self.effect, self.key)

    def _to_px(self, x, y) -> QPointF:
        r = self._area(); return QPointF(r.left() + x * r.width(), r.bottom() - y * r.height())

    def _area(self) -> QRectF:
        return QRectF(8, 8, self.width() - 16, self.height() - 16)

    def _from_px(self, pos) -> tuple[float, float]:
        r = self._area()
        return (min(1, max(0, (pos.x() - r.left()) / r.width())), min(1, max(0, (r.bottom() - pos.y()) / r.height())))

    def _hit(self, pos) -> int | None:
        for i, (x, y) in enumerate(self.pts):
            q = self._to_px(x, y)
            if abs(q.x() - pos.x()) < 9 and abs(q.y() - pos.y()) < 9:
                return i
        return None

    def mousePressEvent(self, e):
        i = self._hit(e.position())
        if e.button() == Qt.RightButton and i is not None and len(self.pts) > 1:
            self.pts.pop(i); self.changed.emit(); self.update()
        elif e.button() == Qt.LeftButton:
            self.drag = i; self.update()

    def mouseDoubleClickEvent(self, e):
        if self._hit(e.position()) is None:
            self.pts.append(self._from_px(e.position())); self.pts.sort()
            self.changed.emit(); self.update()

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            self.pts[self.drag] = self._from_px(e.position())
            self.changed.emit(); self.update()

    def mouseReleaseEvent(self, _):
        if self.drag is not None:
            self.pts.sort(); self.drag = None; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self._area(); p.fillRect(self.rect(), QColor("#1b1d23"))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        for k in range(1, 4):
            p.drawLine(QPointF(r.left() + r.width() * k / 4, r.top()), QPointF(r.left() + r.width() * k / 4, r.bottom()))
            p.drawLine(QPointF(r.left(), r.top() + r.height() * k / 4), QPointF(r.right(), r.top() + r.height() * k / 4))
        col = QColor(dict((k, c) for k, _l, c in CHANNELS)[self.key])
        path = QPainterPath()
        for i in range(201):
            q = self._to_px(i / 200, curve_value(self.pts, i / 200))
            path.moveTo(q) if i == 0 else path.lineTo(q)
        p.setPen(QPen(col, 2)); p.drawPath(path)
        p.setBrush(col)
        for x, y in self.pts:
            p.drawEllipse(self._to_px(x, y), 5, 5)


class ColorEffectEditor(QWidget):
    changed = Signal(object)

    def __init__(self, effect: ColorEffect | None = None):
        super().__init__()
        self.effect = effect or ColorEffect()
        self.swatch_row = QHBoxLayout()
        self.sw_box = QWidget(); self.sw_box.setLayout(self.swatch_row)
        self.curve = CurveEdit(self.effect); self.curve.changed.connect(lambda: self.changed.emit(self.effect))
        self.mode_btn = QPushButton("Swatch"); self.mode_btn.setCheckable(True)
        self.mode_btn.toggled.connect(self._mode)
        self.chan_btns = []
        tabs = QHBoxLayout(); tabs.addWidget(self.mode_btn)
        for key, label, _c in CHANNELS:
            b = QPushButton(label); b.setCheckable(True); b.clicked.connect(lambda _=0, k=key: self._chan(k))
            self.chan_btns.append(b); tabs.addWidget(b)
        tabs.addStretch()
        self.dur = QDoubleSpinBox(); self.dur.setRange(0.1, 600); self.dur.setSuffix(" s"); self.dur.setValue(self.effect.duration)
        self.dur.valueChanged.connect(self._dur); tabs.addWidget(self.dur)
        lay = QVBoxLayout(self); lay.addLayout(tabs); lay.addWidget(self.sw_box); lay.addWidget(self.curve)
        self._chan("hue"); self.mode_btn.setChecked(self.effect.mode == "swatches"); self._mode(self.effect.mode == "swatches")
        self.rebuild_swatches()

    def _mode(self, swatches: bool):
        self.effect.mode = "swatches" if swatches else "curves"
        self.mode_btn.setText("Swatch" if swatches else "Curve")
        self.sw_box.setVisible(swatches); self.curve.setVisible(not swatches)
        for b in self.chan_btns:
            b.setVisible(not swatches)
        self.changed.emit(self.effect)

    def _chan(self, key):
        self.curve.key = key
        for b, (k, _l, _c) in zip(self.chan_btns, CHANNELS):
            b.setChecked(k == key)
        self.curve.update()

    def _dur(self, v):
        self.effect.duration = v; self.changed.emit(self.effect)

    def rebuild_swatches(self):
        while self.swatch_row.count():
            w = self.swatch_row.takeAt(0).widget()
            if w:
                w.setParent(None)
        for i, (r, g, b) in enumerate(self.effect.swatches):
            btn = QPushButton(); btn.setFixedSize(64, 64)
            btn.setStyleSheet(f"background:rgb({r},{g},{b});border:1px solid #33363f;border-radius:6px;")
            btn.clicked.connect(lambda _=0, i=i: self.edit_swatch(i))
            self.swatch_row.addWidget(btn)
        plus = QPushButton("+"); plus.setFixedSize(64, 64); plus.clicked.connect(self.add_swatch)
        self.swatch_row.addWidget(plus); self.swatch_row.addStretch()

    def add_swatch(self, rgb=(255, 255, 255)):
        if not isinstance(rgb, tuple):
            rgb = (255, 255, 255)
        self.effect.swatches.append(rgb); self.rebuild_swatches(); self.changed.emit(self.effect)

    def edit_swatch(self, i: int, color: QColor | None = None):
        c = color or QColorDialog.getColor(QColor(*self.effect.swatches[i]), self)
        if c.isValid():
            self.effect.swatches[i] = (c.red(), c.green(), c.blue()); self.rebuild_swatches(); self.changed.emit(self.effect)
