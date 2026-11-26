"""Workspace Status (manuale 4.1): schede Avvisi, Logs e Triggers. La scheda Video Metrics di QLab non c'è."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..cue.logs import CATEGORIES
from .cue_active import WarningsWindow

TRIGGER_KINDS = {"hotkey": "Tasto", "midi": "MIDI", "wall_clock": "Orologio", "timecode": "Timecode"}


def describe_trigger(kind: str, value) -> str:
    if kind == "hotkey":
        return str(value)
    if isinstance(value, dict):
        return ", ".join("%s=%s" % (key, item) for key, item in value.items())
    return str(value)


def trigger_rows(workspace) -> list[dict]:
    """Un dict per ogni trigger attivo dei cue: cue, tipo e descrizione."""
    rows = []
    for cue in workspace.all_cues():
        for kind, value in cue.triggers.items():
            if value:
                rows.append({"cue": cue, "number": cue.number, "name": cue.display_name(workspace),
                             "kind": TRIGGER_KINDS.get(kind, kind), "detail": describe_trigger(kind, value)})
    return rows


class LogsTab(QWidget):
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.boxes = {}
        for category, title in CATEGORIES.items():
            box = QCheckBox(title)
            box.setChecked(runtime.logs.enabled(category))
            box.toggled.connect(lambda checked, chosen=category: self.runtime.logs.set_enabled(chosen, checked))
            row.addWidget(box)
            self.boxes[category] = box
        layout.addLayout(row)
        filter_row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtro")
        self.filter.textChanged.connect(self.refresh)
        clear_button = QPushButton("Svuota")
        clear_button.clicked.connect(self.clear)
        filter_row.addWidget(self.filter, 1)
        filter_row.addWidget(clear_button)
        layout.addLayout(filter_row)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

    def refresh(self) -> None:
        lines = self.runtime.logs.lines(None, self.filter.text())
        text = "\n".join(lines[-500:])
        if text != self.text.toPlainText():
            self.text.setPlainText(text)

    def clear(self) -> None:
        self.runtime.logs.clear()
        self.refresh()


class TriggersTab(QWidget):
    cue_chosen = Signal(str)

    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["N.", "Nome", "Tipo", "Dettaglio"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.cellClicked.connect(self._clicked)
        layout.addWidget(self.table)
        self.rows: list[dict] = []
        self.refresh()

    def refresh(self) -> None:
        self.rows = trigger_rows(self.runtime.workspace)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            for column, key in enumerate(("number", "name", "kind", "detail")):
                item = QTableWidgetItem(str(row[key]))
                item.setData(256, row["cue"].unique_id)
                self.table.setItem(index, column, item)
        self.table.setSortingEnabled(True)

    def _clicked(self, row: int, column: int) -> None:
        item = self.table.item(row, 0)
        if item is not None:
            self.cue_chosen.emit(item.data(256))


class WorkspaceStatusWindow(QWidget):
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        self.setWindowTitle("Workspace Status")
        self.resize(720, 460)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.warnings = WarningsWindow(runtime)
        self.logs = LogsTab(runtime)
        self.triggers = TriggersTab(runtime)
        self.tabs.addTab(self.warnings, "Avvisi")
        self.tabs.addTab(self.logs, "Logs")
        self.tabs.addTab(self.triggers, "Triggers")
        layout.addWidget(self.tabs)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.logs.refresh)
        self.timer.start(500)

    def refresh_all(self) -> None:
        self.warnings.refresh()
        self.triggers.refresh()
        self.logs.refresh()
