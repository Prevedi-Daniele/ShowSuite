"""Editor delle patch del workspace Cue: audio, ingressi audio, MIDI, rete, stage e route video.

Ogni patch è una riga di tabella; il numero di riga (da 1) è il numero di patch usato dai cue.
Le regioni degli stage sono modificate come JSON. I nomi dei dispositivi sono testo libero (nessun elenco da hardware)."""
from __future__ import annotations

import json

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..cue.model import Workspace

# (chiave patch, titolo scheda, [(campo, intestazione, tipo, valore iniziale)])
PATCH_KINDS = [
    ("audio", "Uscite audio", [("name", "Nome", str, "Audio"), ("device", "Dispositivo", str, ""),
                               ("first_channel", "Primo canale", int, 1), ("channels", "Canali", int, 2)]),
    ("audio_input", "Ingressi audio", [("name", "Nome", str, "Ingresso"), ("device", "Dispositivo", str, ""),
                                       ("first_channel", "Primo canale", int, 1), ("channels", "Canali", int, 1)]),
    ("midi", "MIDI", [("name", "Nome", str, "MIDI"), ("device", "Porta", str, "")]),
    ("network", "Rete", [("name", "Nome", str, "Rete"), ("kind", "Tipo (udp/tcp)", str, "udp"),
                         ("host", "Host", str, "127.0.0.1"), ("port", "Porta", int, 53000)]),
    ("video_stage", "Stage video", [("name", "Nome", str, "Stage"), ("width", "Larghezza", int, 1920),
                                    ("height", "Altezza", int, 1080), ("regions", "Regioni (JSON)", list, [])]),
    ("video_route", "Route video", [("name", "Nome", str, "Uscita"), ("stage", "Stage (n.)", int, 1),
                                    ("region", "Regione", str, "")]),
]


class PatchDialog(QDialog):
    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patch del workspace")
        self.resize(720, 420)
        self.workspace = workspace
        self.tables: dict[str, QTableWidget] = {}
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        for key, title, columns in PATCH_KINDS:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            table = QTableWidget(0, len(columns))
            table.setHorizontalHeaderLabels([column[1] for column in columns])
            table.horizontalHeader().setStretchLastSection(True)
            self.tables[key] = table
            for entry in workspace.patches.get(key, []):
                self._append_row(key, entry)
            page_layout.addWidget(table)
            row = QHBoxLayout()
            add_button = QPushButton("Aggiungi")
            add_button.clicked.connect(lambda checked=False, kind=key: self.add_patch(kind))
            remove_button = QPushButton("Rimuovi")
            remove_button.clicked.connect(lambda checked=False, kind=key: self.remove_patch(kind))
            row.addWidget(add_button)
            row.addWidget(remove_button)
            row.addStretch(1)
            page_layout.addLayout(row)
            tabs.addTab(page, title)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_checked)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _columns(key: str) -> list:
        for kind_key, title, columns in PATCH_KINDS:
            if kind_key == key:
                return columns
        return []

    def _append_row(self, key: str, entry: dict) -> None:
        table = self.tables[key]
        row = table.rowCount()
        table.insertRow(row)
        for column_index, (field, header, kind, default) in enumerate(self._columns(key)):
            value = entry.get(field, default)
            text = json.dumps(value) if kind is list else str(value)
            table.setItem(row, column_index, QTableWidgetItem(text))

    def add_patch(self, key: str) -> None:
        defaults = {field: default for field, header, kind, default in self._columns(key)}
        defaults["name"] = "%s %d" % (defaults.get("name", "Patch"), self.tables[key].rowCount() + 1)
        self._append_row(key, defaults)

    def remove_patch(self, key: str) -> None:
        table = self.tables[key]
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def collect(self) -> dict:
        """Legge le tabelle e restituisce {tipo: [patch]}. Solleva ValueError con il punto errato."""
        result = {}
        for key, title, columns in PATCH_KINDS:
            entries = []
            table = self.tables[key]
            for row in range(table.rowCount()):
                entry = {}
                for column_index, (field, header, kind, default) in enumerate(columns):
                    item = table.item(row, column_index)
                    text = item.text() if item is not None else ""
                    try:
                        if kind is int:
                            entry[field] = int(text)
                        elif kind is list:
                            entry[field] = json.loads(text) if text.strip() != "" else []
                        else:
                            entry[field] = text
                    except ValueError:
                        raise ValueError("%s, riga %d, «%s»: valore non valido" % (title, row + 1, header))
                entries.append(entry)
            result[key] = entries
        return result

    def _accept_checked(self) -> None:
        try:
            self.collect()
        except ValueError as error:
            QMessageBox.warning(self, "Patch", str(error))
            return
        self.accept()

    def apply(self) -> None:
        collected = self.collect()
        for key, entries in collected.items():
            self.workspace.patches[key] = entries
        self.workspace.modified = True
