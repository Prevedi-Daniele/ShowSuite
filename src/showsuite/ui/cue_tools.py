"""Finestre di servizio della sezione Cue: Paste Cue Properties, Override Controls, Timecode Status."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..cue.properties import GROUPS
from ..cue.protocols import seconds_to_timecode

OVERRIDE_ROWS = [("Musical MIDI", "midiInput", "midiOutput"), ("MIDI Show Control", "mscInput", "mscOutput"),
                 ("MIDI SysEx", "sysexInput", "sysexOutput"),
                 ("Rete (altri dispositivi)", "networkExternalInput", "networkExternalOutput"),
                 ("Rete (locale)", "networkLocalInput", "networkLocalOutput"),
                 ("Timecode", "timecodeInput", "timecodeOutput"), ("Art-Net e USB DMX", None, "dmxOutput")]


class PastePropertiesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incolla proprietà")
        layout = QVBoxLayout(self)
        self.boxes = {}
        for key, (title, _attributes) in GROUPS.items():
            box = QCheckBox(title)
            box.setChecked(key in ("timing", "appearance"))
            layout.addWidget(box)
            self.boxes[key] = box
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def chosen_groups(self) -> list[str]:
        return [key for key, box in self.boxes.items() if box.isChecked() == True]


class OverrideControlsWindow(QWidget):
    """Sospende ingressi/uscite per tipo di segnale. Scrive in `workspace.settings["overrides"]`:
    casella spuntata = sospeso (valore interno False). Come in QLab è un controllo del workspace, non globale."""

    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self.setWindowTitle("Override Controls")
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Segnale"), 0, 0)
        layout.addWidget(QLabel("Sospendi ingresso"), 0, 1)
        layout.addWidget(QLabel("Sospendi uscita"), 0, 2)
        self.boxes = {}
        for row, (title, input_key, output_key) in enumerate(OVERRIDE_ROWS, start=1):
            layout.addWidget(QLabel(title), row, 0)
            for column, key in ((1, input_key), (2, output_key)):
                if key is None:
                    continue
                box = QCheckBox()
                box.setChecked(workspace.settings["overrides"].get(key, True) == False)
                box.toggled.connect(lambda checked, chosen=key: self.set_override(chosen, checked))
                layout.addWidget(box, row, column)
                self.boxes[key] = box
        self.status = QLabel("")
        layout.addWidget(self.status, len(OVERRIDE_ROWS) + 1, 0, 1, 3)
        self._update_status()

    def set_override(self, key: str, suspended: bool) -> None:
        self.workspace.settings["overrides"][key] = suspended == False
        self.workspace.modified = True
        self._update_status()

    def active_overrides(self) -> list[str]:
        return [key for key, value in self.workspace.settings["overrides"].items() if value == False]

    def _update_status(self) -> None:
        active = self.active_overrides()
        self.status.setText("Override attivi: " + ", ".join(active) if len(active) > 0 else "Nessun override attivo")
        self.status.setStyleSheet("color: #d33;" if len(active) > 0 else "")


class TimecodeStatusWindow(QWidget):
    """Timecode in ingresso per ogni lista/cart con sync: ultima posizione, stato e secondi dall'ultimo pacchetto."""
    HEADERS = ["Lista", "Formato", "Posizione", "Stato", "Ultimo segnale"]

    def __init__(self, runtime, triggers):
        super().__init__()
        self.runtime = runtime
        self.triggers = triggers
        self.setWindowTitle("Timecode Status")
        self.resize(560, 220)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(250)
        self.refresh()

    def rows(self) -> list[list[str]]:
        result = []
        now = self.runtime.clock.now()
        for cue_list in self.runtime.workspace.lists:
            for container in cue_list.walk():
                if container.params.get("timecode_sync", False) == False:
                    continue
                state = self.triggers.timecode_state.get(container.unique_id)
                format_index = int(container.params.get("timecode_format", 1))
                if state is None or state["last"] is None:
                    result.append([container.name or container.number or "(senza nome)", str(format_index), "--:--:--:--",
                                   "nessun segnale", ""])
                    continue
                hours, minutes, seconds, frames = seconds_to_timecode(state["last"], format_index)
                age = now - state["last_arrival"]
                result.append([container.name or container.number or "(senza nome)", str(format_index),
                               "%02d:%02d:%02d:%02d" % (hours, minutes, seconds, frames),
                               "in corso" if state["running"] == True else "fermo", "%.1f s fa" % age])
        return result

    def refresh(self) -> None:
        rows = self.rows()
        self.table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, text in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(text))
