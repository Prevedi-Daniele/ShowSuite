"""Finestra Fixture Options (come in Lightkey): limiti dimmer, Grand Master, range/offset pan-tilt, disabilita."""
from __future__ import annotations

from PySide6.QtWidgets import (QColorDialog, QComboBox, QCheckBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QVBoxLayout)


class FixtureOptionsDialog(QDialog):
    def __init__(self, fixtures, parent=None):
        super().__init__(parent)
        self.fixtures = list(fixtures)
        f0 = self.fixtures[0]
        self.setWindowTitle("Fixture Options")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b>{f0.name}</b>" + (f" (+{len(self.fixtures) - 1})" if len(self.fixtures) > 1 else "")))
        form = QFormLayout(); lay.addLayout(form)
        self.dmin = QSpinBox(); self.dmin.setRange(0, 255); self.dmin.setValue(f0.dimmer_min)
        self.dmax = QSpinBox(); self.dmax.setRange(0, 255); self.dmax.setValue(f0.dimmer_max)
        self.ignore = QCheckBox("Ignora il Master Dimmer"); self.ignore.setChecked(f0.ignore_master)
        self.pan_range = QDoubleSpinBox(); self.pan_range.setRange(1, 3600); self.pan_range.setValue(f0.pan_range)
        self.tilt_range = QDoubleSpinBox(); self.tilt_range.setRange(1, 3600); self.tilt_range.setValue(f0.tilt_range)
        self.pan_off = QDoubleSpinBox(); self.pan_off.setRange(-720, 720); self.pan_off.setValue(f0.pan_offset)
        self.tilt_off = QDoubleSpinBox(); self.tilt_off.setRange(-720, 720); self.tilt_off.setValue(f0.tilt_offset)
        self.disabled = QCheckBox("Disabilita fixture"); self.disabled.setChecked(f0.disabled)
        self.beam = QPushButton(f0.beam_color or "Automatico"); self.beam_color = f0.beam_color
        self.beam.clicked.connect(self._pick_beam)
        self.namepos = QComboBox(); self.namepos.addItems(["below", "above", "hidden"]); self.namepos.setCurrentText(f0.name_pos)
        self.icon = QDoubleSpinBox(); self.icon.setRange(0.5, 2.0); self.icon.setSingleStep(0.1); self.icon.setValue(f0.icon_size)
        for lab, w in (("Colore raggio", self.beam), ("Posizione nome", self.namepos), ("Dimensione simbolo", self.icon),
                       ("Dimmer minimo (DMX)", self.dmin), ("Dimmer massimo (DMX)", self.dmax), ("", self.ignore),
                       ("Range pan (°)", self.pan_range), ("Range tilt (°)", self.tilt_range),
                       ("Offset pan (°)", self.pan_off), ("Offset tilt (°)", self.tilt_off), ("", self.disabled)):
            form.addRow(lab, w)
        row = QHBoxLayout()
        cancel = QPushButton("Annulla"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Fatto"); ok.clicked.connect(self.apply)
        row.addWidget(cancel); row.addWidget(ok); lay.addLayout(row)

    def _pick_beam(self):
        c = QColorDialog.getColor(parent=self)
        self.beam_color = c.name() if c.isValid() else ""
        self.beam.setText(self.beam_color or "Automatico")

    def apply(self):
        lo, hi = sorted((self.dmin.value(), self.dmax.value()))
        for f in self.fixtures:
            f.dimmer_min, f.dimmer_max = lo, hi
            f.ignore_master = self.ignore.isChecked()
            f.pan_range, f.tilt_range = self.pan_range.value(), self.tilt_range.value()
            f.pan_offset, f.tilt_offset = self.pan_off.value(), self.tilt_off.value()
            f.disabled = self.disabled.isChecked()
            f.beam_color, f.name_pos, f.icon_size = self.beam_color, self.namepos.currentText(), self.icon.value()
        self.accept()
