from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLineEdit, QListWidget, QVBoxLayout

from ..light.search import SCOPES, search


class SearchDialog(QDialog):
    chosen = Signal(str, str)      # scope, nome

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project; self.setWindowTitle("Cerca nel progetto"); self.resize(420, 360)
        lay = QVBoxLayout(self)
        self.q = QLineEdit(); self.q.setPlaceholderText("Cerca…"); lay.addWidget(self.q)
        row = QHBoxLayout(); self.boxes = {}
        for s in SCOPES:
            b = QCheckBox(s); b.setChecked(True); b.toggled.connect(self.run); row.addWidget(b); self.boxes[s] = b
        lay.addLayout(row)
        self.list = QListWidget(); lay.addWidget(self.list)
        self.q.textChanged.connect(self.run)
        self.list.itemActivated.connect(lambda it: self.chosen.emit(*it.data(Qt.UserRole)))

    def run(self, *_):
        self.list.clear()
        for scope, name, det in search(self.project, self.q.text(), [s for s, b in self.boxes.items() if b.isChecked()]):
            it = self.list.addItem(f"[{scope}] {name}" + (f" — {det}" if det else ""))
            self.list.item(self.list.count() - 1).setData(Qt.UserRole, (scope, name))
