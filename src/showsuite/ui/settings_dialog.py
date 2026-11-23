from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QVBoxLayout)

from ..light import settings as S

QUIT = (("ask", "Chiedi se salvare"), ("save", "Salva sempre"), ("discard", "Non salvare"))


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni"); self.cfg = S.load()
        lay = QVBoxLayout(self); form = QFormLayout(); lay.addLayout(form)
        self.quit = QComboBox()
        for k, lab in QUIT:
            self.quit.addItem(lab, k)
        self.quit.setCurrentIndex([k for k, _ in QUIT].index(self.cfg["on_quit"]))
        self.last = QCheckBox("Riapri l'ultimo progetto all'avvio"); self.last.setChecked(self.cfg["open_last"])
        self.adapt = QCheckBox("Sfondo Preview adattivo al colore"); self.adapt.setChecked(self.cfg["adaptive_background"])
        self.pw = QLineEdit(); self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("vuoto = lascia com'è")
        self.clear_pw = QCheckBox("Rimuovi password di blocco")
        form.addRow("Prima di chiudere", self.quit); form.addRow("", self.last); form.addRow("", self.adapt)
        form.addRow("Nuova password blocco", self.pw); form.addRow("", self.clear_pw)
        row = QHBoxLayout(); ok = QPushButton("Fatto"); ok.clicked.connect(self.apply)
        cancel = QPushButton("Annulla"); cancel.clicked.connect(self.reject)
        row.addWidget(cancel); row.addWidget(ok); lay.addLayout(row)

    def apply(self):
        c = self.cfg
        c["on_quit"] = self.quit.currentData(); c["open_last"] = self.last.isChecked()
        c["adaptive_background"] = self.adapt.isChecked()
        if self.clear_pw.isChecked():
            c["lock_password"] = ""
        elif self.pw.text():
            c["lock_password"] = S.hash_pw(self.pw.text())
        S.save(c); self.accept()
