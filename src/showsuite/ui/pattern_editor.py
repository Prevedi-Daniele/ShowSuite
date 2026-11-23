"""Editor degli effetti a pattern: scelta del pattern, campioni (colori), parametri, ordine dei fixture, tempi."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..light.patfx import (DEFAULTS, ORDER_TITLES, ORDERS, ORIGINS, PATTERN_TITLES, PATTERNS, PatternEffect)

PERCENT = {"phase", "time_offset", "delay", "smoothness", "fringe", "noise", "center", "steepness", "sparking", "cooling"}
INTEGER = {"steps_per_value", "length", "distance", "overshoot", "trail", "count"}
BOOLEAN = {"palette"}


class PatternEditor(QWidget):
    changed = Signal(object)

    def __init__(self, effect: PatternEffect | None = None):
        super().__init__()
        self.effect = effect or PatternEffect()
        self.pat_btns: dict[str, QPushButton] = {}
        row = QHBoxLayout()
        for p in PATTERNS:
            b = QPushButton(PATTERN_TITLES[p]); b.setCheckable(True); b.clicked.connect(lambda _=0, p=p: self.set_pattern(p))
            self.pat_btns[p] = b; row.addWidget(b)
        self.sample_row = QHBoxLayout(); self.sample_box = QWidget(); self.sample_box.setLayout(self.sample_row)
        self.form = QFormLayout(); self.form_box = QWidget(); self.form_box.setLayout(self.form)
        # tempi e ordine
        self.dur = QDoubleSpinBox(); self.dur.setRange(0.05, 600); self.dur.setSuffix(" s"); self.dur.setValue(self.effect.duration)
        self.dur.valueChanged.connect(lambda v: self._set("duration", v))
        self.beat = QCheckBox("Beat-controlled"); self.beat.toggled.connect(lambda v: self._set("beat_controlled", v))
        self.mult = QComboBox(); self.mult.addItems(["÷4", "÷2", "×1", "×2", "×4"]); self.mult.setCurrentIndex(2)
        self.mult.currentIndexChanged.connect(lambda i: self._set("beat_mult", (0.25, 0.5, 1.0, 2.0, 4.0)[i]))
        self.order = QComboBox(); self.order.addItems([ORDER_TITLES[o] for o in ORDERS])
        self.order.currentIndexChanged.connect(lambda i: self._set("order", ORDERS[i]))
        self.origin = QComboBox(); self.origin.addItems(["Start to End", "From Center", "To Center"])
        self.origin.currentIndexChanged.connect(lambda i: self._set("origin", ORIGINS[i]))
        self.group = QSpinBox(); self.group.setRange(1, 64); self.group.valueChanged.connect(lambda v: self._set("grouping", v))
        self.repeat = QSpinBox(); self.repeat.setRange(0, 64); self.repeat.valueChanged.connect(lambda v: self._set("repeat", v))
        side = QFormLayout()
        for lab, w in (("Duration", self.dur), ("", self.beat), ("Beat multiplier", self.mult), ("Fixture Order", self.order),
                       ("Origin", self.origin), ("Grouping", self.group), ("Repeat", self.repeat)):
            side.addRow(lab, w)
        body = QHBoxLayout(); mid = QVBoxLayout(); mid.addWidget(self.sample_box); mid.addWidget(self.form_box); mid.addStretch()
        body.addLayout(mid, 1); body.addLayout(side)
        lay = QVBoxLayout(self); lay.addLayout(row); lay.addLayout(body)
        self.set_pattern(self.effect.pattern, emit=False)

    def _set(self, attr: str, value) -> None:
        setattr(self.effect, attr, value); self.changed.emit(self.effect)

    def set_pattern(self, name: str, emit: bool = True) -> None:
        e = self.effect
        e.pattern = name
        e.params = {k: v for k, v in e.params.items() if k in DEFAULTS[name]}
        for p, b in self.pat_btns.items():
            b.setChecked(p == name)
        self.rebuild_params(); self.rebuild_samples()
        if emit:
            self.changed.emit(e)

    def rebuild_params(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        e = self.effect
        for key, default in DEFAULTS[e.pattern].items():
            val = e.params.get(key, default)
            if key in BOOLEAN:
                w = QCheckBox(); w.setChecked(bool(val)); w.toggled.connect(lambda v, k=key: self._param(k, 1 if v else 0))
            elif key in INTEGER:
                w = QSpinBox(); w.setRange(0, 999); w.setValue(int(val)); w.valueChanged.connect(lambda v, k=key: self._param(k, v))
            elif key in PERCENT:
                w = QSpinBox(); w.setRange(0, 100); w.setSuffix(" %"); w.setValue(round(val * 100))
                w.valueChanged.connect(lambda v, k=key: self._param(k, v / 100))
            else:
                w = QDoubleSpinBox(); w.setRange(0.01, 60); w.setSingleStep(0.05); w.setDecimals(2); w.setValue(float(val))
                w.valueChanged.connect(lambda v, k=key: self._param(k, v))
            w.setMaximumWidth(140)
            self.form.addRow(key.replace("_", " ").title(), w)

    def _param(self, key: str, value) -> None:
        self.effect.params[key] = value; self.changed.emit(self.effect)

    def rebuild_samples(self) -> None:
        while self.sample_row.count():
            w = self.sample_row.takeAt(0).widget()
            if w:
                w.setParent(None)
        for i, (r, g, b) in enumerate(self.effect.samples):
            btn = QPushButton(); btn.setFixedSize(54, 54)
            btn.setStyleSheet(f"background:rgb({r},{g},{b});border:1px solid #33363f;border-radius:6px;")
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.clicked.connect(lambda _=0, i=i: self.edit_sample(i))
            btn.customContextMenuRequested.connect(lambda _p, i=i: self.delete_sample(i))
            btn.setToolTip("Clic: cambia colore • clic destro: elimina")
            self.sample_row.addWidget(btn)
        plus = QPushButton("+"); plus.setFixedSize(54, 54); plus.clicked.connect(lambda: self.add_sample())
        self.sample_row.addWidget(plus); self.sample_row.addStretch()

    def add_sample(self, rgb=(255, 255, 255)) -> None:
        if not isinstance(rgb, tuple):
            rgb = (255, 255, 255)
        self.effect.samples.append(rgb); self.rebuild_samples(); self.changed.emit(self.effect)

    def delete_sample(self, i: int) -> None:
        if len(self.effect.samples) > 1:
            del self.effect.samples[i]; self.rebuild_samples(); self.changed.emit(self.effect)

    def edit_sample(self, i: int, color: QColor | None = None) -> None:
        c = color or QColorDialog.getColor(QColor(*self.effect.samples[i]), self)
        if c.isValid():
            self.effect.samples[i] = (c.red(), c.green(), c.blue()); self.rebuild_samples(); self.changed.emit(self.effect)

    def duplicate_sample(self, i: int) -> None:
        self.effect.samples.insert(i + 1, self.effect.samples[i]); self.rebuild_samples(); self.changed.emit(self.effect)
