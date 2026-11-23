"""Editor profili fixture: nome, canali (tipo, default, 16 bit, intervalli), salva in libreria, importa/esporta."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ..light import userlib as U
from ..light.fixtures import ChannelDef, FixtureProfile

HEAD = ("Canale", "Tipo", "Default", "16 bit", "Intervalli (0-9:Closed; 10-255:Strobe)")


class ProfileEditor(QDialog):
    def __init__(self, profile: FixtureProfile | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor profilo fixture"); self.resize(760, 460)
        self.result_profile: FixtureProfile | None = None
        lay = QVBoxLayout(self); form = QFormLayout(); lay.addLayout(form)
        p = profile
        self.maker = QLineEdit(p.manufacturer if p else ""); self.model = QLineEdit(p.model if p else "")
        self.mode = QLineEdit(p.mode if p else "")
        form.addRow("Costruttore", self.maker); form.addRow("Modello", self.model); form.addRow("Modalità", self.mode)
        self.table = QTableWidget(0, len(HEAD)); self.table.setHorizontalHeaderLabels(HEAD)
        self.table.horizontalHeader().setStretchLastSection(True); lay.addWidget(self.table)
        for c in (p.channels if p else (ChannelDef("Dimmer", kind="intensity"),)):
            self.add_row(c)
        row = QHBoxLayout(); lay.addLayout(row)
        for lab, fn in (("+ Canale", lambda: self.add_row()), ("− Rimuovi", self.remove_row),
                        ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1))):
            b = QPushButton(lab); b.clicked.connect(lambda _=0, fn=fn: fn()); row.addWidget(b)
        self.info = QLabel(); row.addWidget(self.info, 1)
        row2 = QHBoxLayout(); lay.addLayout(row2)
        imp = QPushButton("Importa…"); imp.clicked.connect(self.do_import)
        exp = QPushButton("Esporta…"); exp.clicked.connect(self.do_export)
        cancel = QPushButton("Annulla"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Salva in libreria"); ok.clicked.connect(self.save)
        for b in (imp, exp):
            row2.addWidget(b)
        row2.addStretch(); row2.addWidget(cancel); row2.addWidget(ok)
        self.table.itemChanged.connect(lambda *_: self._count())
        self._count()

    def add_row(self, c: ChannelDef | None = None):
        c = c or ChannelDef(f"Canale {self.table.rowCount() + 1}")
        r = self.table.rowCount(); self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(c.name))
        k = QComboBox(); k.addItems(U.KINDS); k.setCurrentText(c.kind); self.table.setCellWidget(r, 1, k)
        d = QSpinBox(); d.setRange(0, 65535); d.setValue(c.default); self.table.setCellWidget(r, 2, d)
        f = QCheckBox(); f.setChecked(c.fine); self.table.setCellWidget(r, 3, f)
        self.table.setItem(r, 4, QTableWidgetItem(U.caps_to_text(c.caps)))
        self._count()

    def remove_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r); self._count()

    def move(self, d: int):
        try:
            ch = list(self.build().channels)
        except ValueError:
            return
        r = self.table.currentRow(); n = r + d
        if r < 0 or not 0 <= n < len(ch):
            return
        ch[r], ch[n] = ch[n], ch[r]
        self.table.setRowCount(0)
        for c in ch:
            self.add_row(c)
        self.table.setCurrentCell(n, 0)

    def _count(self):
        if not hasattr(self, "info"):
            return
        try:
            self.info.setText(f"{self.build().footprint} canali DMX")
        except ValueError as e:
            self.info.setText(str(e))

    def build(self) -> FixtureProfile:
        ch = []
        for r in range(self.table.rowCount()):
            name = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            caps = U.text_to_caps(self.table.item(r, 4).text() if self.table.item(r, 4) else "")
            ch.append(ChannelDef(name, self.table.cellWidget(r, 2).value(), self.table.cellWidget(r, 3).isChecked(),
                                 self.table.cellWidget(r, 1).currentText(), caps))
        return FixtureProfile(self.maker.text().strip(), self.model.text().strip(), self.mode.text().strip(), tuple(ch))

    def save(self):
        try:
            p = self.build(); U.save_profile(p)
        except ValueError as e:
            QMessageBox.warning(self, "Profilo", str(e)); return
        self.result_profile = p; self.accept()

    def do_export(self):
        f, _ = QFileDialog.getSaveFileName(self, "Esporta profilo", "", "Profilo (*.json)")
        if f:
            try:
                U.export_profile(self.build(), f)
            except ValueError as e:
                QMessageBox.warning(self, "Profilo", str(e))

    def do_import(self):
        f, _ = QFileDialog.getOpenFileName(self, "Importa profilo", "", "Profilo (*.json)")
        if f:
            try:
                p = U.import_profile(f)
            except Exception as e:
                QMessageBox.warning(self, "Profilo", str(e)); return
            self.maker.setText(p.manufacturer); self.model.setText(p.model); self.mode.setText(p.mode)
            self.table.setRowCount(0)
            for c in p.channels:
                self.add_row(c)
