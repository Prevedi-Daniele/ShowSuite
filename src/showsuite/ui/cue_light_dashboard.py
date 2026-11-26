"""Light Dashboard della sezione Cue: pannello per pilotare la sezione Light dal workspace dei Cue.

Con il bridge locale mostra le fixture (slider intensità), i cue Live (Avvia/Rilascia), master e blackout.
Con il bridge remoto (OSC verso un'altra istanza di Light) resta solo la console dei comandi, perché non c'è modo di leggere
il patch dall'altra parte. La console accetta lo stesso linguaggio del Light cue (vedi `cue/lightbridge.py`).
Non è il Light dashboard di QLab (che dipende da macOS/Lightkey): è un equivalente."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QSlider, QTableWidget,
                               QVBoxLayout, QWidget)

from ..cue.lightbridge import parse_command


def light_fixture_names(bridge) -> list[str]:
    runner = getattr(bridge, "runner", None)
    if runner is None:
        return []
    return [fixture.name for fixture in runner.engine.project.patch.fixtures]


def light_cue_names(bridge) -> list[str]:
    runner = getattr(bridge, "runner", None)
    if runner is None:
        return []
    return [live_cue.name for live_cue in runner.engine.project.cues]


class LightDashboardWindow(QWidget):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("Light Dashboard")
        self.resize(520, 560)
        layout = QVBoxLayout(self)
        self.local = getattr(bridge, "runner", None) is not None
        self.fixture_table = QTableWidget(0, 2)
        self.fixture_table.setHorizontalHeaderLabels(["Fixture", "Intensità"])
        self.fixture_table.horizontalHeader().setStretchLastSection(True)
        self.cue_list = QListWidget()
        self.sliders: dict[str, QSlider] = {}
        if self.local == True:
            layout.addWidget(QLabel("Fixture"))
            layout.addWidget(self.fixture_table)
            layout.addWidget(QLabel("Cue Live"))
            layout.addWidget(self.cue_list)
            row = QHBoxLayout()
            self.start_button = QPushButton("Avvia cue")
            self.start_button.clicked.connect(lambda: self.run_selected_cue(True))
            self.release_button = QPushButton("Rilascia cue")
            self.release_button.clicked.connect(lambda: self.run_selected_cue(False))
            self.blackout_button = QPushButton("Blackout")
            self.blackout_button.setCheckable(True)
            self.blackout_button.toggled.connect(self.set_blackout)
            self.clear_button = QPushButton("Clear programmer")
            self.clear_button.clicked.connect(self.clear_programmer)
            for button in (self.start_button, self.release_button, self.blackout_button, self.clear_button):
                row.addWidget(button)
            layout.addLayout(row)
            master_row = QHBoxLayout()
            master_row.addWidget(QLabel("Master"))
            self.master_slider = QSlider(Qt.Horizontal)
            self.master_slider.setRange(0, 100)
            self.master_slider.setValue(100)
            self.master_slider.valueChanged.connect(self.set_master)
            master_row.addWidget(self.master_slider)
            layout.addLayout(master_row)
        else:
            layout.addWidget(QLabel("Bridge remoto: solo console (il patch di Light non è leggibile da qui)."))
        self.console = QLineEdit()
        self.console.setPlaceholderText("es.  Par 1.Red 100   |   cue Rosso   |   master 50   |   osc /blackout 1")
        self.console.returnPressed.connect(self.run_console)
        layout.addWidget(self.console)
        self.log = QListWidget()
        self.log.setMaximumHeight(110)
        layout.addWidget(self.log)
        self.refresh()

    # --- contenuto ---
    def refresh(self) -> None:
        if self.local == False:
            return
        names = light_fixture_names(self.bridge)
        self.fixture_table.setRowCount(len(names))
        self.sliders = {}
        for index, name in enumerate(names):
            self.fixture_table.setItem(index, 0, _read_only_item(name))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.valueChanged.connect(lambda value, fixture=name: self.set_fixture(fixture, value))
            self.fixture_table.setCellWidget(index, 1, slider)
            self.sliders[name] = slider
        self.cue_list.clear()
        for name in light_cue_names(self.bridge):
            self.cue_list.addItem(name)

    # --- azioni ---
    def set_fixture(self, fixture: str, percent: int) -> None:
        self.execute({"kind": "fixture", "fixture": fixture, "channel": "", "value": percent / 100.0})

    def run_selected_cue(self, start: bool) -> None:
        item = self.cue_list.currentItem()
        if item is None:
            self.report("nessun cue selezionato")
            return
        self.execute({"kind": "cue", "name": item.text(), "on": start})

    def set_blackout(self, on: bool) -> None:
        self.execute({"kind": "plain", "action": "blackout", "value": 1.0 if on == True else 0.0})

    def set_master(self, percent: int) -> None:
        self.execute({"kind": "plain", "action": "master", "value": percent / 100.0})

    def clear_programmer(self) -> None:
        try:
            self.bridge.dashboard(["clear"], [])
            self.report("programmer azzerato")
        except Exception as error:
            self.report("errore: " + str(error))

    def run_console(self) -> None:
        line = self.console.text().strip()
        if line == "":
            return
        try:
            command = parse_command(line)
        except ValueError as error:
            self.report("errore: " + str(error))
            return
        self.execute(command)
        self.console.clear()

    def execute(self, command: dict) -> bool:
        try:
            self.bridge.apply(command)
        except Exception as error:
            self.report("errore: " + str(error))
            return False
        self.report("ok: " + _describe(command))
        return True

    def report(self, message: str) -> None:
        self.log.insertItem(0, message)
        while self.log.count() > 50:
            self.log.takeItem(self.log.count() - 1)


def _describe(command: dict) -> str:
    kind = command["kind"]
    if kind == "cue":
        return ("avvia " if command["on"] == True else "rilascia ") + command["name"]
    if kind == "plain":
        return "%s %d" % (command["action"], round(command["value"] * 100))
    if kind == "fixture":
        target = command["fixture"] + ("." + command["channel"] if command["channel"] != "" else "")
        return "%s %d" % (target, round(command["value"] * 100))
    return "osc " + command["address"]


def _read_only_item(text: str):
    from PySide6.QtWidgets import QTableWidgetItem
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    return item
