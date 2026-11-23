"""Finestra Fanning: proprietà, valore iniziale/finale, curva, simmetrico. Ordine: da sinistra a destra."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QPushButton, QSlider,
                               QVBoxLayout)
from PySide6.QtCore import Qt

from ..light.fanning import CURVES, FAN_PROPS, fan


class FanDialog(QDialog):
    def __init__(self, engine, names, parent=None):
        super().__init__(parent)
        self.engine, self.names = engine, names
        self.setWindowTitle("Fanning")
        lay = QVBoxLayout(self); form = QFormLayout(); lay.addLayout(form)
        self.prop = QComboBox(); self.prop.addItems(FAN_PROPS)
        self.curve = QComboBox(); self.curve.addItems(list(CURVES))
        self.start = QSlider(Qt.Horizontal); self.end = QSlider(Qt.Horizontal)
        for s, v in ((self.start, 0), (self.end, 100)):
            s.setRange(0, 100); s.setValue(v)
        self.sym = QCheckBox("Simmetrico")
        for lab, w in (("Proprietà", self.prop), ("Inizio", self.start), ("Fine", self.end),
                       ("Curva", self.curve), ("", self.sym)):
            form.addRow(lab, w)
        row = QHBoxLayout(); ok = QPushButton("Applica"); ok.clicked.connect(self.apply)
        close = QPushButton("Chiudi"); close.clicked.connect(self.accept)
        row.addWidget(close); row.addWidget(ok); lay.addLayout(row)
        for w in (self.prop, self.curve):
            w.currentIndexChanged.connect(lambda *_: self.apply())
        for w in (self.start, self.end):
            w.valueChanged.connect(lambda *_: self.apply())
        self.sym.toggled.connect(lambda *_: self.apply())

    def apply(self):
        fan(self.engine, self.names, self.prop.currentText(), self.start.value() / 100, self.end.value() / 100,
            self.curve.currentText(), self.sym.isChecked())
