"""Finestra Find: cerca cue per testo in numero, nome, note, tipo o target e li seleziona nell'elenco."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

FIELDS = ("number", "name", "notes", "type", "target")


def find_cues(workspace, text: str, fields: tuple = FIELDS, case_sensitive: bool = False) -> list:
    """Cue della lista attiva (con figli) che contengono `text` in uno dei campi scelti, in ordine di elenco."""
    needle = text if case_sensitive == True else text.lower()
    if needle == "":
        return []
    found = []
    for cue in workspace.active_list().walk():
        if cue.parent is None:
            continue
        values = []
        if "number" in fields:
            values.append(cue.number)
        if "name" in fields:
            values.append(cue.name if cue.name != "" else cue.default_name(workspace))
        if "notes" in fields:
            values.append(cue.notes)
        if "type" in fields:
            values.append(cue.cue_type)
        if "target" in fields:
            values.append(cue.target_number)
        for value in values:
            haystack = value if case_sensitive == True else value.lower()
            if needle in haystack:
                found.append(cue)
                break
    return found


class FindWindow(QWidget):
    cue_chosen = Signal(str)

    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self.setWindowTitle("Find")
        self.resize(420, 360)
        layout = QVBoxLayout(self)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Cerca in numero, nome, note, tipo, target")
        self.query.textChanged.connect(self.search)
        layout.addWidget(self.query)
        row = QHBoxLayout()
        self.boxes = {}
        for key, label in (("number", "Numero"), ("name", "Nome"), ("notes", "Note"), ("type", "Tipo"), ("target", "Target")):
            box = QCheckBox(label)
            box.setChecked(True)
            box.toggled.connect(lambda checked: self.search())
            row.addWidget(box)
            self.boxes[key] = box
        layout.addLayout(row)
        self.case_box = QCheckBox("Maiuscole/minuscole")
        self.case_box.toggled.connect(lambda checked: self.search())
        layout.addWidget(self.case_box)
        self.results = QListWidget()
        self.results.itemActivated.connect(self._activated)
        self.results.itemClicked.connect(self._activated)
        layout.addWidget(self.results)
        self.count_label = QLabel("")
        layout.addWidget(self.count_label)

    def search(self) -> None:
        fields = tuple(key for key, box in self.boxes.items() if box.isChecked() == True)
        cues = find_cues(self.workspace, self.query.text(), fields, self.case_box.isChecked())
        self.results.clear()
        for cue in cues:
            label = (cue.number + "  " if cue.number != "" else "") + (cue.name if cue.name != "" else cue.default_name(self.workspace))
            item = QListWidgetItem(label + "   [" + cue.cue_type + "]")
            item.setData(Qt.UserRole, cue.unique_id)
            self.results.addItem(item)
        self.count_label.setText("%d trovati" % len(cues))

    def _activated(self, item) -> None:
        self.cue_chosen.emit(item.data(Qt.UserRole))
