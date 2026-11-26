"""Editor dedicati per i cue Audio/Video: matrice dei livelli, slice e envelope integrato."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..cue.model import Cue

MINUS_INFINITY = -200.0


def parse_decibel(text: str) -> float:
    cleaned = text.strip().lower().replace("db", "").strip()
    if cleaned in ("", "-inf", "inf", "off", "-∞"):
        return MINUS_INFINITY
    return float(cleaned.replace(",", "."))


def format_decibel(value: float) -> str:
    return "-inf" if value <= MINUS_INFINITY else ("%.1f" % value).rstrip("0").rstrip(".")


def output_count(cue: Cue, workspace=None) -> int:
    """Uscite cue mostrate: dalla patch del cue se nota, altrimenti 2 (o più se ci sono livelli espliciti)."""
    count = 2
    if workspace is not None:
        patches = workspace.patches.get("audio", [])
        number = int(cue.params.get("audio_output_patch", 1))
        if 1 <= number <= len(patches):
            count = int(patches[number - 1].get("cue_outputs", patches[number - 1].get("channels", 2)))
    for key in cue.params.get("levels", {}):
        if "/" in key:
            count = max(count, int(key.split("/")[1]))
    return count


class LevelsEditor(QWidget):
    """Matrice ingressi × uscite cue in dB, più main e trim. Le celle vuote seguono il default (diagonale 0 dB)."""
    changed = Signal()

    def __init__(self, workspace=None):
        super().__init__()
        self.workspace = workspace
        self.cue: Cue | None = None
        self._loading = False
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.main = QDoubleSpinBox()
        self.main.setRange(-200.0, 12.0)
        self.main.setSuffix(" dB")
        self.main.valueChanged.connect(self._set_main)
        self.trim = QDoubleSpinBox()
        self.trim.setRange(-60.0, 24.0)
        self.trim.setSuffix(" dB")
        self.trim.valueChanged.connect(self._set_trim)
        form.addRow("Main", self.main)
        form.addRow("Trim", self.trim)
        layout.addLayout(form)
        self.table = QTableWidget(0, 0)
        self.table.itemChanged.connect(self._cell_changed)
        layout.addWidget(self.table)
        reset = QPushButton("Ripristina matrice")
        reset.clicked.connect(self.reset_matrix)
        layout.addWidget(reset)

    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        self.table.clear()
        if cue is None:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self._loading = False
            return
        levels = cue.params.get("levels", {})
        self.main.setValue(float(levels.get("main", 0.0)))
        self.trim.setValue(float(cue.params.get("trim", 0.0)))
        rows = max(1, int(cue.params.get("media_channels") or 2))
        columns = output_count(cue, self.workspace)
        self.table.setRowCount(rows)
        self.table.setColumnCount(columns)
        self.table.setHorizontalHeaderLabels(["Out %d" % (column + 1) for column in range(columns)])
        self.table.setVerticalHeaderLabels(["In %d" % (row + 1) for row in range(rows)])
        for row in range(rows):
            for column in range(columns):
                self.table.setItem(row, column, QTableWidgetItem(format_decibel(self.crosspoint(row, column))))
        self._loading = False

    def crosspoint(self, row: int, column: int) -> float:
        levels = self.cue.params.get("levels", {})
        explicit = [key for key in levels if "/" in key]
        key = "%d/%d" % (row + 1, column + 1)
        if len(explicit) == 0:
            return 0.0 if row == column else MINUS_INFINITY
        return float(levels.get(key, MINUS_INFINITY))

    def set_crosspoint(self, row: int, column: int, decibel: float) -> None:
        levels = self.cue.params.setdefault("levels", {})
        if len([key for key in levels if "/" in key]) == 0:
            for diagonal in range(min(self.table.rowCount(), self.table.columnCount())):
                levels["%d/%d" % (diagonal + 1, diagonal + 1)] = 0.0
        levels["%d/%d" % (row + 1, column + 1)] = decibel
        self.changed.emit()

    def reset_matrix(self) -> None:
        if self.cue is None:
            return
        levels = self.cue.params.setdefault("levels", {})
        for key in [key for key in levels if "/" in key]:
            del levels[key]
        self.load(self.cue)
        self.changed.emit()

    def _cell_changed(self, item: QTableWidgetItem) -> None:
        if self._loading == True or self.cue is None:
            return
        try:
            value = parse_decibel(item.text())
        except ValueError:
            self._loading = True
            item.setText(format_decibel(self.crosspoint(item.row(), item.column())))
            self._loading = False
            return
        self.set_crosspoint(item.row(), item.column(), value)

    def _set_main(self, value: float) -> None:
        if self._loading == False and self.cue is not None:
            self.cue.params.setdefault("levels", {})["main"] = float(value)
            self.changed.emit()

    def _set_trim(self, value: float) -> None:
        if self._loading == False and self.cue is not None:
            self.cue.params["trim"] = float(value)
            self.changed.emit()


class SliceEditor(QWidget):
    """Tempo di inizio/fine e slice con play count (0 = infinito: salvato come "inf")."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.cue: Cue | None = None
        self._loading = False
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.start = QDoubleSpinBox()
        self.start.setRange(0.0, 100000.0)
        self.start.setSuffix(" s")
        self.start.valueChanged.connect(lambda value: self._set_param("start_time", float(value)))
        self.end = QDoubleSpinBox()
        self.end.setRange(0.0, 100000.0)
        self.end.setSuffix(" s")
        self.end.valueChanged.connect(lambda value: self._set_param("end_time", float(value)))
        self.rate = QDoubleSpinBox()
        self.rate.setRange(0.03, 33.0)
        self.rate.setDecimals(3)
        self.rate.valueChanged.connect(lambda value: self._set_param("rate", float(value)))
        self.loop = QCheckBox("Loop infinito del cue")
        self.loop.toggled.connect(lambda state: self._set_param("infinite_loop", bool(state)))
        form.addRow("Inizio", self.start)
        form.addRow("Fine", self.end)
        form.addRow("Velocità", self.rate)
        form.addRow(self.loop)
        layout.addLayout(form)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Marker (s)", "Play count (0 = ∞)"])
        self.table.itemChanged.connect(self._cell_changed)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        add_button = QPushButton("Aggiungi slice")
        add_button.clicked.connect(self.add_slice)
        remove_button = QPushButton("Rimuovi")
        remove_button.clicked.connect(self.remove_selected)
        row.addWidget(add_button)
        row.addWidget(remove_button)
        layout.addLayout(row)

    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        self.table.setRowCount(0)
        if cue is not None:
            self.start.setValue(float(cue.params.get("start_time", 0.0)))
            end_value = cue.params.get("end_time")
            self.end.setValue(float(end_value) if end_value is not None else float(cue.params.get("media_duration") or 0.0))
            self.rate.setValue(float(cue.params.get("rate", 1.0)))
            self.loop.setChecked(bool(cue.params.get("infinite_loop", False)))
            for item in cue.params.get("slices", []):
                self._append_row(float(item["time"]), item.get("play_count", 1))
        self._loading = False

    def _append_row(self, time_value: float, count) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        infinite = count in ("inf", "infinite") or (isinstance(count, str) and count.isalpha())
        self.table.setItem(row, 0, QTableWidgetItem("%g" % time_value))
        self.table.setItem(row, 1, QTableWidgetItem("0" if infinite else str(int(count))))

    def collect(self) -> list:
        slices = []
        for row in range(self.table.rowCount()):
            try:
                time_value = float(self.table.item(row, 0).text().replace(",", "."))
                count = int(self.table.item(row, 1).text())
            except (ValueError, AttributeError):
                continue
            slices.append({"time": max(0.0, time_value), "play_count": "inf" if count <= 0 else count})
        slices.sort(key=lambda item: item["time"])
        return slices

    def _store(self) -> None:
        if self._loading == False and self.cue is not None:
            self.cue.params["slices"] = self.collect()
            self.changed.emit()

    def add_slice(self) -> None:
        if self.cue is None:
            return
        self._loading = True
        self._append_row(float(self.end.value()) / 2.0, 1)
        self._loading = False
        self._store()

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._store()

    def _cell_changed(self, item) -> None:
        self._store()

    def _set_param(self, key: str, value) -> None:
        if self._loading == False and self.cue is not None:
            self.cue.params[key] = value
            self.changed.emit()


class EnvelopeCurve(QWidget):
    """Anteprima dell'envelope: punti [secondi, dB]."""

    def __init__(self):
        super().__init__()
        self.points: list = []
        self.setMinimumHeight(90)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#222"))
        painter.setPen(QPen(QColor("#555")))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        if len(self.points) < 2:
            return
        ordered = sorted(self.points, key=lambda item: item[0])
        end_time = max(ordered[-1][0], 0.001)
        low = min(-60.0, min(item[1] for item in ordered))
        high = max(12.0, max(item[1] for item in ordered))
        painter.setPen(QPen(QColor("#4fc3f7"), 2))
        previous = None
        for time_value, decibel in ordered:
            point = QPointF(self.width() * time_value / end_time,
                            self.height() * (1.0 - (max(decibel, low) - low) / (high - low)))
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point


class EnvelopeEditor(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.cue: Cue | None = None
        self._loading = False
        layout = QVBoxLayout(self)
        self.enabled = QCheckBox("Usa envelope integrato")
        self.enabled.toggled.connect(self._toggle)
        layout.addWidget(self.enabled)
        self.curve = EnvelopeCurve()
        layout.addWidget(self.curve)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Tempo (s)", "Livello (dB)"])
        self.table.itemChanged.connect(lambda item: self._store())
        layout.addWidget(self.table)
        row = QHBoxLayout()
        add_button = QPushButton("Aggiungi punto")
        add_button.clicked.connect(self.add_point)
        remove_button = QPushButton("Rimuovi")
        remove_button.clicked.connect(self.remove_selected)
        row.addWidget(add_button)
        row.addWidget(remove_button)
        layout.addLayout(row)

    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        self.table.setRowCount(0)
        if cue is not None:
            fade = cue.params.get("integrated_fade", {})
            self.enabled.setChecked(bool(fade.get("enabled", False)))
            for time_value, decibel in fade.get("points", []):
                self._append_row(float(time_value), float(decibel))
            self.curve.points = list(fade.get("points", []))
        self.curve.update()
        self._loading = False

    def _append_row(self, time_value: float, decibel: float) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("%g" % time_value))
        self.table.setItem(row, 1, QTableWidgetItem(format_decibel(decibel)))

    def collect(self) -> list:
        points = []
        for row in range(self.table.rowCount()):
            try:
                points.append([max(0.0, float(self.table.item(row, 0).text().replace(",", "."))),
                               parse_decibel(self.table.item(row, 1).text())])
            except (ValueError, AttributeError):
                continue
        points.sort(key=lambda item: item[0])
        return points

    def _store(self) -> None:
        if self._loading == True or self.cue is None:
            return
        fade = self.cue.params.setdefault("integrated_fade", {"enabled": False, "curve": "custom",
                                                              "lock_to_cue": False, "points": []})
        fade["points"] = self.collect()
        self.curve.points = fade["points"]
        self.curve.update()
        self.changed.emit()

    def _toggle(self, state: bool) -> None:
        if self._loading == False and self.cue is not None:
            self.cue.params.setdefault("integrated_fade", {"points": []})["enabled"] = bool(state)
            self.changed.emit()

    def add_point(self) -> None:
        if self.cue is None:
            return
        last = self.collect()[-1][0] if self.table.rowCount() > 0 else 0.0
        self._loading = True
        self._append_row(last + 1.0, 0.0)
        self._loading = False
        self._store()

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._store()
