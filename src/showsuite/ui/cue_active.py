"""Finestra Active Cues e finestra Avvisi (cue broken) del workspace Cue."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from ..cue.engine import Runtime
from ..cue.timeutil import format_time


def active_rows(runtime: Runtime) -> list[dict]:
    """Un dict per ogni cue attivo (pre-wait, azione, post-wait, pausa o dissolvenza in uscita)."""
    rows = []
    for state in list(runtime.states.values()):
        if state.is_active() == False:
            continue
        cue = state.cue
        status = runtime.status(cue)
        if status["pre_wait_running"] == True:
            phase = "Pre-wait"
            elapsed = status["pre_wait_elapsed"]
            total = cue.pre_wait
        elif status["paused"] == True:
            phase = "In pausa"
            elapsed = status["action_elapsed"]
            total = status["action_duration"]
        else:
            phase = "In corso" if status["running"] == True else "Post-wait"
            elapsed = status["action_elapsed"] if status["running"] == True else status["post_wait_elapsed"]
            total = status["action_duration"] if status["running"] == True else cue.post_wait
        rows.append({"cue": cue, "number": cue.number, "name": cue.display_name(), "phase": phase,
                     "elapsed": elapsed, "total": total})
    rows.sort(key=lambda row: row["number"])
    return rows


def warning_rows(runtime: Runtime) -> list[dict]:
    rows = []
    for cue in runtime.workspace.all_cues():
        reason = runtime.broken_reason(cue)
        if reason != "":
            rows.append({"cue": cue, "number": cue.number, "name": cue.display_name(), "reason": reason})
    return rows


class ActiveCuesWindow(QWidget):
    def __init__(self, runtime: Runtime):
        super().__init__()
        self.setWindowTitle("Active Cues")
        self.runtime = runtime
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["N.", "Nome", "Stato", "Trascorso", "Durata"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        for label, action in (("Pause", self.pause_selected), ("Resume", self.resume_selected),
                              ("Stop", self.stop_selected), ("Panic", self.panic_selected)):
            button = QPushButton(label)
            button.clicked.connect(action)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)

    def showEvent(self, event) -> None:
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self.timer.stop()
        super().hideEvent(event)

    def refresh(self) -> None:
        self.rows = active_rows(self.runtime)
        self.table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            total = row["total"]
            values = [row["number"], row["name"], row["phase"], format_time(row["elapsed"]),
                      "∞" if total == float("inf") else format_time(total)]
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))

    def _selected(self) -> list:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        return [self.rows[row]["cue"] for row in rows if row < len(self.rows)]

    def pause_selected(self) -> None:
        for cue in self._selected():
            self.runtime.pause_cue(cue)

    def resume_selected(self) -> None:
        for cue in self._selected():
            self.runtime.resume_cue(cue)

    def stop_selected(self) -> None:
        for cue in self._selected():
            self.runtime.stop_cue(cue)

    def panic_selected(self) -> None:
        for cue in self._selected():
            self.runtime.panic_cue(cue)


class WarningsWindow(QWidget):
    def __init__(self, runtime: Runtime):
        super().__init__()
        self.setWindowTitle("Avvisi")
        self.runtime = runtime
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["N.", "Nome", "Problema"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)
        refresh_button = QPushButton("Aggiorna")
        refresh_button.clicked.connect(self.refresh)
        layout.addWidget(refresh_button)
        self.refresh()

    def refresh(self) -> None:
        rows = warning_rows(self.runtime)
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, key in enumerate(("number", "name", "reason")):
                self.table.setItem(index, column, QTableWidgetItem(str(row[key])))
