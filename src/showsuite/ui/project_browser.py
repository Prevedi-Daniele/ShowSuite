"""Project Browser (come in Lightkey): all'avvio mostra i progetti recenti, Nuovo e Apri."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from ..light import recents


class ProjectBrowser(QDialog):
    """Dopo exec(): `choice` = ("new", None) | ("open", None) | ("path", percorso) | None (annullato)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ShowSuite Light — Progetti"); self.resize(480, 380)
        self.choice: tuple | None = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<h3>Progetti recenti</h3>"))
        self.list = QListWidget(); lay.addWidget(self.list, 1)
        for p in recents.load():
            if os.path.exists(p):
                it = QListWidgetItem(f"{os.path.basename(p)}\n{os.path.dirname(p)}"); it.setData(Qt.UserRole, p); self.list.addItem(it)
        if not self.list.count():
            self.list.addItem("(nessun progetto recente)"); self.list.item(0).setFlags(Qt.NoItemFlags)
        self.list.itemActivated.connect(self._open_item)
        row = QHBoxLayout(); lay.addLayout(row)
        for lab, kind in (("Nuovo progetto", "new"), ("Apri…", "open")):
            b = QPushButton(lab); b.clicked.connect(lambda _=0, k=kind: self._done((k, None))); row.addWidget(b)
        row.addStretch()
        b = QPushButton("Apri selezionato"); b.clicked.connect(lambda: self._open_item(self.list.currentItem())); row.addWidget(b)

    def _open_item(self, it):
        if it and it.data(Qt.UserRole):
            self._done(("path", it.data(Qt.UserRole)))

    def _done(self, choice):
        self.choice = choice; self.accept()
