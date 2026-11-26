"""Editor dedicati ai cue Network, MIDI e Fade (e widget curva condiviso)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..cue.curves import CURVE_TYPES, default_curve, evaluate
from ..cue.model import Cue

MINUS_INFINITY = -200.0
MIDI_STATUS_NAMES = ["Note Off", "Note On", "Key Pressure", "Control Change", "Program Change", "Channel Pressure",
                     "Pitch Bend"]
MSC_COMMAND_NAMES = ["GO", "STOP", "RESUME", "TIMED_GO", "LOAD", "SET", "FIRE", "ALL_OFF", "RESTORE", "RESET",
                     "GO_OFF", "GO/JAM_CLOCK", "STANDBY_+", "STANDBY_-", "SEQUENCE_+", "SEQUENCE_-", "START_CLOCK",
                     "STOP_CLOCK", "ZERO_CLOCK", "SET_CLOCK", "MTC_CHASE_ON", "MTC_CHASE_OFF", "OPEN_CUE_LIST",
                     "CLOSE_CUE_LIST", "OPEN_CUE_PATH", "CLOSE_CUE_PATH"]


class BoundEditor(QWidget):
    """Base: widget legati a chiavi di cue.params; load() li aggiorna senza scrivere, le modifiche scrivono e notificano."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.cue: Cue | None = None
        self._loading = False
        self.bindings: list = []

    def bind(self, widget, key: str, kind: str):
        self.bindings.append((widget, key, kind))
        if kind == "int":
            widget.valueChanged.connect(lambda value, name=key: self._write(name, int(value)))
        elif kind == "float":
            widget.valueChanged.connect(lambda value, name=key: self._write(name, float(value)))
        elif kind == "bool":
            widget.toggled.connect(lambda value, name=key: self._write(name, bool(value)))
        elif kind == "text":
            widget.editingFinished.connect(lambda name=key, field=widget: self._write(name, field.text()))
        elif kind == "index":
            widget.currentIndexChanged.connect(lambda value, name=key: self._write(name, int(value)))
        elif kind == "data":
            widget.currentIndexChanged.connect(lambda value, name=key, field=widget: self._write(name, field.currentData()))
        return widget

    def _write(self, key: str, value) -> None:
        if self._loading == True or self.cue is None:
            return
        self.cue.params[key] = value
        self.changed.emit()

    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        if cue is not None:
            for widget, key, kind in self.bindings:
                value = cue.params.get(key)
                if kind == "int":
                    widget.setValue(int(value if value is not None else 0))
                elif kind == "float":
                    widget.setValue(float(value if value is not None else 0.0))
                elif kind == "bool":
                    widget.setChecked(bool(value))
                elif kind == "text":
                    widget.setText("" if value is None else str(value))
                elif kind == "index":
                    widget.setCurrentIndex(int(value if value is not None else 0))
                elif kind == "data":
                    index = widget.findData(value)
                    widget.setCurrentIndex(max(0, index))
        self._after_load()
        self._loading = False

    def _after_load(self) -> None:
        pass

    @staticmethod
    def spin(low: int, high: int) -> QSpinBox:
        widget = QSpinBox()
        widget.setRange(low, high)
        return widget

    @staticmethod
    def double(low: float, high: float, decimals: int = 3) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setDecimals(decimals)
        widget.setRange(low, high)
        return widget


class CurvePreview(QWidget):
    def __init__(self):
        super().__init__()
        self.curve = default_curve()
        self.setMinimumHeight(70)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#222"))
        painter.setPen(QPen(QColor("#4fc3f7"), 2))
        previous = None
        for step in range(0, 61):
            position = step / 60.0
            point = QPointF(position * (self.width() - 1), (1.0 - evaluate(self.curve, position)) * (self.height() - 1))
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point


class CurveEditor(BoundEditor):
    """Tipo e intensità della curva (le curve custom si modificano come punti nel campo JSON dell'Inspector)."""

    def __init__(self, key: str = "curve"):
        super().__init__()
        self.key = key
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.kind = QComboBox()
        self.kind.addItems(CURVE_TYPES)
        self.kind.currentTextChanged.connect(self._change_kind)
        self.intensity = self.double(0.0, 1.0, 2)
        self.intensity.valueChanged.connect(self._change_intensity)
        self.preview = CurvePreview()
        layout.addRow("Curva", self.kind)
        layout.addRow("Intensità", self.intensity)
        layout.addRow(self.preview)

    def _curve(self) -> dict:
        return self.cue.params.setdefault(self.key, default_curve())

    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        if cue is not None:
            curve = cue.params.get(self.key) or default_curve()
            self.kind.setCurrentText(curve.get("type", "s_curve"))
            self.intensity.setValue(float(curve.get("intensity", 0.5)))
            self.preview.curve = curve
            self.preview.update()
        self._loading = False

    def _change_kind(self, text: str) -> None:
        if self._loading == False and self.cue is not None:
            self._curve()["type"] = text
            self.preview.curve = self._curve()
            self.preview.update()
            self.changed.emit()

    def _change_intensity(self, value: float) -> None:
        if self._loading == False and self.cue is not None:
            self._curve()["intensity"] = float(value)
            self.preview.curve = self._curve()
            self.preview.update()
            self.changed.emit()


class NetworkEditor(BoundEditor):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.patch = self.bind(self.spin(1, 64), "network_patch", "int")
        self.kind = self.bind(QComboBox(), "message_kind", "data")
        for label, value in (("OSC", "osc"), ("UDP", "udp"), ("TCP", "tcp")):
            self.kind.addItem(label, value)
        self.message = self.bind(QLineEdit(), "message", "text")
        self.message.setPlaceholderText("/cue/1/start   oppure   /fader $1")
        self.fade_type = self.bind(QComboBox(), "fade_type", "index")
        self.fade_type.addItems(["Nessun fade", "1 valore ($1)", "2 valori ($1 $2)"])
        self.number_type = self.bind(QComboBox(), "number_type", "index")
        self.number_type.addItems(["Intero", "Decimale"])
        self.fade_from = self.bind(self.double(-1000000, 1000000), "fade_from", "float")
        self.fade_to = self.bind(self.double(-1000000, 1000000), "fade_to", "float")
        self.fps = self.bind(self.spin(1, 120), "fps", "int")
        self.curve = CurveEditor()
        self.curve.changed.connect(self.changed.emit)
        layout.addRow("Patch di rete", self.patch)
        layout.addRow("Protocollo", self.kind)
        layout.addRow("Messaggio", self.message)
        layout.addRow("Fade", self.fade_type)
        layout.addRow("Tipo numeri", self.number_type)
        layout.addRow("Da", self.fade_from)
        layout.addRow("A", self.fade_to)
        layout.addRow("Aggiornamenti/s", self.fps)
        layout.addRow(self.curve)

    def _after_load(self) -> None:
        self.curve.load(self.cue)
        for widget in (self.fade_from, self.fade_to, self.fps, self.number_type, self.curve):
            widget.setEnabled(int(self.cue.params.get("fade_type", 0)) != 0)

    def _write(self, key: str, value) -> None:
        super()._write(key, value)
        if key == "fade_type" and self._loading == False and self.cue is not None:
            for widget in (self.fade_from, self.fade_to, self.fps, self.number_type, self.curve):
                widget.setEnabled(int(value) != 0)


class MidiEditor(BoundEditor):
    """Campi mostrati secondo il tipo: 1 voce, 2 MSC, 3 SysEx."""

    def __init__(self):
        super().__init__()
        self.layout_form = QFormLayout(self)
        self.patch = self.bind(self.spin(1, 64), "midi_patch", "int")
        self.message_type = QComboBox()
        self.message_type.addItems(["Voce MIDI", "MIDI Show Control", "SysEx"])
        self.message_type.currentIndexChanged.connect(self._change_type)
        self.status = self.bind(QComboBox(), "status", "index")
        self.status.addItems(MIDI_STATUS_NAMES)
        self.channel = self.bind(self.spin(1, 16), "channel", "int")
        self.byte1 = self.bind(self.spin(0, 16383), "byte1", "int")
        self.byte2 = self.bind(self.spin(0, 127), "byte2", "int")
        self.end_value = QLineEdit()
        self.end_value.setPlaceholderText("vuoto = nessun fade")
        self.end_value.editingFinished.connect(self._change_end_value)
        self.command_format = self.bind(self.spin(1, 127), "command_format", "int")
        self.command = self.bind(QComboBox(), "command", "data")
        for number, name in enumerate(MSC_COMMAND_NAMES, 1):
            self.command.addItem(name, number)
        self.device_id = self.bind(self.spin(0, 127), "device_id", "int")
        self.q_number = self.bind(QLineEdit(), "q_number", "text")
        self.q_list = self.bind(QLineEdit(), "q_list", "text")
        self.q_path = self.bind(QLineEdit(), "q_path", "text")
        self.control_number = self.bind(self.spin(0, 16383), "control_number", "int")
        self.control_value = self.bind(self.spin(0, 16383), "control_value", "int")
        self.raw = self.bind(QLineEdit(), "raw_string", "text")
        self.raw.setPlaceholderText("F0 7E 7F 09 01 F7")
        self.rows = {"voice": [("Stato", self.status), ("Canale", self.channel), ("Byte 1 / nota", self.byte1),
                               ("Byte 2 / velocity", self.byte2), ("Valore finale (fade)", self.end_value)],
                     "msc": [("Formato comando", self.command_format), ("Comando", self.command),
                             ("ID dispositivo", self.device_id), ("Q number", self.q_number), ("Q list", self.q_list),
                             ("Q path", self.q_path), ("Controllo", self.control_number),
                             ("Valore controllo", self.control_value)],
                     "sysex": [("Byte esadecimali", self.raw)]}
        self.layout_form.addRow("Patch MIDI", self.patch)
        self.layout_form.addRow("Tipo", self.message_type)
        self.labels: dict = {}
        for group in self.rows.values():
            for label, widget in group:
                self.layout_form.addRow(label, widget)
                self.labels[widget] = self.layout_form.labelForField(widget)

    def visible_group(self) -> str:
        return ("voice", "msc", "sysex")[max(0, min(2, self.message_type.currentIndex()))]

    def _refresh_visibility(self) -> None:
        current = self.visible_group()
        for group, items in self.rows.items():
            for label, widget in items:
                widget.setVisible(group == current)
                self.labels[widget].setVisible(group == current)

    def _after_load(self) -> None:
        self.message_type.setCurrentIndex(int(self.cue.params.get("message_type", 1)) - 1)
        end_value = self.cue.params.get("end_value")
        self.end_value.setText("" if end_value is None else str(end_value))
        self._refresh_visibility()

    def _change_type(self, index: int) -> None:
        self._refresh_visibility()
        if self._loading == False and self.cue is not None:
            self.cue.params["message_type"] = index + 1
            self.changed.emit()

    def _change_end_value(self) -> None:
        if self._loading == True or self.cue is None:
            return
        text = self.end_value.text().strip()
        self.cue.params["end_value"] = int(text) if text.lstrip("-").isdigit() else None
        self.changed.emit()


class FadeEditor(BoundEditor):
    """Fade cue: curva, modo assoluto/relativo, parametri video e tabella dei livelli audio (dB)."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.stop_target = self.bind(QCheckBox("Ferma il target a fine fade"), "stop_target_when_done", "bool")
        self.levels_mode = self.bind(QComboBox(), "levels_mode", "data")
        self.levels_mode.addItem("Livelli assoluti", "absolute")
        self.levels_mode.addItem("Livelli relativi", "relative")
        self.do_opacity = self.bind(QCheckBox("Opacità"), "do_opacity", "bool")
        self.opacity = self.bind(self.double(0.0, 1.0, 2), "opacity", "float")
        self.do_rate = self.bind(QCheckBox("Velocità"), "do_rate", "bool")
        self.rate = self.bind(self.double(0.03, 33.0, 3), "rate", "float")
        self.do_rotation = self.bind(QCheckBox("Rotazione Z (°)"), "do_rotation", "bool")
        self.rotation = self.bind(self.double(-3600, 3600, 1), "rotation", "float")
        self.curve = CurveEditor()
        self.curve.changed.connect(self.changed.emit)
        form.addRow(self.stop_target)
        form.addRow("Modo", self.levels_mode)
        form.addRow(self.do_opacity, self.opacity)
        form.addRow(self.do_rate, self.rate)
        form.addRow(self.do_rotation, self.rotation)
        layout.addLayout(form)
        layout.addWidget(self.curve)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Livello (es. main o 1/2)", "dB"])
        self.table.itemChanged.connect(self._table_changed)
        layout.addWidget(self.table)

    def _after_load(self) -> None:
        self.curve.load(self.cue)
        self.table.setRowCount(0)
        for key, value in self.cue.params.get("levels", {}).items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem("-inf" if float(value) <= MINUS_INFINITY else "%g" % value))

    def collect_levels(self) -> dict:
        levels = {}
        for row in range(self.table.rowCount()):
            key_item, value_item = self.table.item(row, 0), self.table.item(row, 1)
            if key_item is None or value_item is None or key_item.text().strip() == "":
                continue
            text = value_item.text().strip().lower()
            try:
                levels[key_item.text().strip()] = MINUS_INFINITY if text in ("", "-inf", "off") else float(text.replace(",", "."))
            except ValueError:
                continue
        return levels

    def add_level(self, key: str, decibel: float = 0.0) -> None:
        self._loading = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(key))
        self.table.setItem(row, 1, QTableWidgetItem("%g" % decibel))
        self._loading = False
        self._table_changed(None)

    def _table_changed(self, item) -> None:
        if self._loading == False and self.cue is not None:
            self.cue.params["levels"] = self.collect_levels()
            self.changed.emit()
