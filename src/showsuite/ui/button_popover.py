"""Popover di un pulsante Live: Contents / Options / Modifiers (come in Lightkey)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QSlider, QSpinBox, QTabBar, QVBoxLayout, QWidget,
                               QStackedWidget)

from ..light.live import CURVES, LiveButton, LiveCue


class ButtonPopover(QDialog):
    def __init__(self, view, btn: LiveButton, cue: LiveCue, parent=None):
        super().__init__(parent or view)
        self.view, self.btn, self.cue = view, btn, cue
        self.setWindowTitle(btn.label or cue.name)
        self.setWindowFlag(Qt.Popup, False)
        self.resize(380, 460)
        self.tabs = QTabBar()
        for t in ("Contents", "Options", "Modifiers"):
            self.tabs.addTab(t)
        self.tabs.setExpanding(True)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._contents()); self.stack.addWidget(self._options()); self.stack.addWidget(self._modifiers())
        self.tabs.currentChanged.connect(self.stack.setCurrentIndex)
        done = QPushButton("Done"); done.clicked.connect(self.accept)
        lay = QVBoxLayout(self); lay.addWidget(self.tabs); lay.addWidget(self.stack, 1); lay.addWidget(done)

    # --- Contents: elenco di ciò che il cue contiene, con × per rimuovere
    def _contents(self) -> QWidget:
        self.items = QListWidget()
        self.items.itemClicked.connect(self._maybe_remove)
        self.refresh_contents()
        box = QWidget(); v = QVBoxLayout(box); v.setContentsMargins(0, 0, 0, 0); v.addWidget(self.items)
        ov = QPushButton("Duplica effetti come overlay"); ov.clicked.connect(self.duplicate_as_overlay); v.addWidget(ov)
        return box

    def refresh_contents(self) -> None:
        c = self.cue
        self.items.clear()

        def add(text: str, key: str | None):
            it = QListWidgetItem(text + ("      ✕" if key else "")); it.setData(Qt.UserRole, key); self.items.addItem(it)
        add(f"Fixture: {', '.join(c.fixtures) or '—'}", None)
        if c.preset:
            add(f"Preset «{c.preset.name}» ({len(c.preset.values)} valori)", "preset")
        if c.steps:
            add(f"Sequenza di {len(c.steps)} step", "steps")
        for i, e in enumerate(c.effects):
            add(f"Effetto: {getattr(e, 'name', type(e).__name__)}", f"effect{i}")
        if c.color_fx:
            add(f"Color Effect ({c.color_fx.mode}, {c.color_fx.duration:g} s)", "color_fx")
        if c.position_fx:
            add(f"Position Effect: {c.position_fx.pattern}", "position_fx")
        if c.pattern_fx:
            add(f"Pattern Effect: {c.pattern_fx.pattern}", "pattern_fx")
        for i, o in enumerate(c.overlays):
            add(f"Overlay: {type(o).__name__.replace('Effect', ' Effect')}", f"overlay{i}")

    def duplicate_as_overlay(self) -> int:
        """Copia gli effetti principali del cue come overlay (da modificare poi con gli strumenti di editing)."""
        import copy
        n = 0
        for fx in (self.cue.color_fx, self.cue.position_fx, self.cue.pattern_fx):
            if fx is not None:
                self.cue.overlays.append(copy.deepcopy(fx)); n += 1
        self.refresh_contents(); return n

    def _maybe_remove(self, item) -> None:
        key = item.data(Qt.UserRole)
        if not key:
            return
        c = self.cue
        if key == "preset":
            c.preset = None
        elif key == "steps":
            c.steps = []
        elif key == "color_fx":
            c.color_fx = None
        elif key == "position_fx":
            c.position_fx = None
        elif key == "pattern_fx":
            c.pattern_fx = None
        elif key.startswith("overlay"):
            del c.overlays[int(key[7:])]
        elif key.startswith("effect"):
            del c.effects[int(key[6:])]
        self.refresh_contents()

    # --- Options
    def _options(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); c, b = self.cue, self.btn
        self.mode = QComboBox(); self.mode.addItems(["Toggle", "Flash"]); self.mode.setCurrentIndex(1 if b.mode == "flash" else 0)
        self.mode.currentIndexChanged.connect(lambda i: (setattr(b, "mode", "flash" if i else "toggle"), setattr(c, "toggle", not i)))
        self.fade_in = QDoubleSpinBox(); self.fade_in.setRange(0, 600); self.fade_in.setSuffix(" s"); self.fade_in.setValue(c.fade_in)
        self.fade_in.valueChanged.connect(lambda v: setattr(c, "fade_in", v))
        self.fade_out = QDoubleSpinBox(); self.fade_out.setRange(0, 600); self.fade_out.setSuffix(" s"); self.fade_out.setValue(c.fade_out)
        self.fade_out.valueChanged.connect(lambda v: setattr(c, "fade_out", v))
        self.curve = QComboBox(); self.curve.addItems(list(CURVES)); self.curve.setCurrentText(c.curve)
        self.curve.currentTextChanged.connect(lambda t: setattr(c, "curve", t))
        self.prio = QSpinBox(); self.prio.setRange(0, 99); self.prio.setValue(c.priority)
        self.prio.valueChanged.connect(lambda v: setattr(c, "priority", v))
        self.startup = QCheckBox("Activate at startup"); self.startup.setChecked(b.startup)
        self.startup.toggled.connect(lambda on: setattr(b, "startup", on))
        self.excl = QCheckBox("Exclude from Live Triggers"); self.excl.setChecked(c.no_trigger)
        self.excl.toggled.connect(lambda on: setattr(c, "no_trigger", on))
        self.edit_curve = QPushButton("Modifica curva…"); self.edit_curve.setVisible(c.curve == "custom")
        self.edit_curve.clicked.connect(self.open_curve_editor)
        self.curve.currentTextChanged.connect(lambda t: self.edit_curve.setVisible(t == "custom"))
        for lab, wd in (("Type", self.mode), ("", self.startup), ("Fade In", self.fade_in), ("Fade Out", self.fade_out),
                        ("Curve", self.curve), ("", self.edit_curve), ("Priority", self.prio), ("", self.excl)):
            f.addRow(lab, wd)
        return w

    def open_curve_editor(self) -> None:
        from .curve_editor import CurveDialog
        d = CurveDialog(self.cue.curve_points, self)
        if d.exec():
            self.cue.curve_points = d.points()

    # --- Modifiers
    def _modifiers(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); c = self.cue
        self.speed = QSlider(Qt.Horizontal); self.speed.setRange(10, 400); self.speed.setValue(round(c.speed * 100))
        self.speed_lbl = QLabel(f"{c.speed:.2f}×")
        self.speed.valueChanged.connect(lambda v: (setattr(c, "speed", v / 100), self.speed_lbl.setText(f"{v / 100:.2f}×")))
        self.dimmer = QSlider(Qt.Horizontal); self.dimmer.setRange(0, 100); self.dimmer.setValue(round(c.dimmer * 100))
        self.dim_lbl = QLabel(f"{round(c.dimmer * 100)} %")
        self.dimmer.valueChanged.connect(lambda v: (setattr(c, "dimmer", v / 100), self.dim_lbl.setText(f"{v} %")))
        from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
        self.bmult = QComboBox()
        for lab, v in (("×¼", 0.25), ("×½", 0.5), ("×1", 1.0), ("×2", 2.0), ("×4", 4.0)):
            self.bmult.addItem(lab, v)
        self.bmult.setCurrentIndex(max(0, self.bmult.findData(c.beat_mult)))
        self.bmult.currentIndexChanged.connect(lambda _: setattr(c, "beat_mult", self.bmult.currentData()))
        self.toff = QDoubleSpinBox(); self.toff.setRange(-64, 64); self.toff.setSuffix(" battute"); self.toff.setValue(c.time_offset)
        self.toff.valueChanged.connect(lambda v: setattr(c, "time_offset", v))
        self.hue = QSlider(Qt.Horizontal); self.hue.setRange(-180, 180); self.hue.setValue(round(c.hue_shift))
        self.hue_lbl = QLabel(f"{round(c.hue_shift)}°")
        self.hue.valueChanged.connect(lambda v: (setattr(c, "hue_shift", float(v)), self.hue_lbl.setText(f"{v}°")))
        for lab, s, l in (("Speed", self.speed, self.speed_lbl), ("Dimmer", self.dimmer, self.dim_lbl),
                          ("Hue", self.hue, self.hue_lbl)):
            row = QHBoxLayout(); row.addWidget(s, 1); row.addWidget(l); f.addRow(lab, row)
        f.addRow("Beat Multiplier", self.bmult); f.addRow("Time Offset", self.toff)
        # altri modificatori del manuale: (chiave, etichetta, min, max, default, suffisso, scala 'add' o 'mul')
        self.mod_widgets = {}
        for key, lab, lo, hi, dflt, suf in (
                ("fade_time", "Fade Time", 0, 400, 100, " %"), ("color_temp", "Color Temperature", -5000, 5000, 0, " K"),
                ("green_sat", "Green Saturation", -100, 100, 0, " %"), ("xfade", "Xfade to Color", 0, 200, 100, " %"),
                ("pan", "Pan Angle", -180, 180, 0, "°"), ("tilt", "Tilt Angle", -180, 180, 0, "°"),
                ("focus", "Focus", 0, 200, 100, " %"), ("zoom", "Zoom Angle", 0, 200, 100, " %"),
                ("iris", "Iris Opening", 0, 200, 100, " %"), ("frost", "Frost Amount", 0, 200, 100, " %"),
                ("fog", "Fog Amount", 0, 200, 100, " %")):
            sp = QSpinBox(); sp.setRange(lo, hi); sp.setSuffix(suf)
            mul = key in ("fade_time", "xfade", "focus", "zoom", "iris", "frost", "fog")
            sp.setValue(round(c.mods.get(key, dflt / 100 if mul else dflt) * (100 if mul else 1)))
            def setter(v, key=key, mul=mul, dflt=dflt):
                if (v == dflt):
                    c.mods.pop(key, None)
                else:
                    c.mods[key] = v / 100 if mul else float(v)
            sp.valueChanged.connect(setter); f.addRow(lab, sp); self.mod_widgets[key] = sp
        return w
