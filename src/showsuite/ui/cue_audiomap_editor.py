"""Audio Map Editor: modifica grafica delle mappe di object audio (manuale QLab 5.2 e 5.6).

Il canvas mostra marks (cerchi), filtri (linee con tacca sul lato attivo) e oggetti (punti colorati); si trascinano con il
mouse. A destra: proprietà dell'elemento scelto, livelli per uscita (solo marks) e anteprima dei livelli risultanti
per l'oggetto scelto. L'instradamento è quello APPROSSIMATO di `cue/audiomap.py`, non quello di QLab."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..cue import audiomap
from .cue_editors import format_decibel, parse_decibel

KINDS = ("marks", "filters", "objects")
KIND_LABELS = {"marks": "Mark", "filters": "Filtro", "objects": "Oggetto"}
PICK_RADIUS = 14.0
COLOR_VALUES = {"berry": "#8e2f5b", "blue": "#3b6fd4", "crimson": "#c0243a", "cyan": "#1fb5c9", "forest": "#2f6b3a",
                "gray": "#888888", "green": "#3fb450", "hot pink": "#ff4fa0", "indigo": "#4b3fa8", "lavender": "#b9a5e6",
                "magenta": "#d43fd4", "midnight": "#1d2a5a", "olive": "#808020", "orange": "#f0902a", "peach": "#f5b895",
                "plum": "#7a3a7a", "purple": "#8a3fd4", "red": "#e03030", "sky blue": "#6ec1f0", "yellow": "#f0d83a",
                "none": "#e8e8e8"}


class MapCanvas(QWidget):
    selection_changed = Signal()
    edited = Signal()

    def __init__(self):
        super().__init__()
        self.audio_map: dict | None = None
        self.selected: tuple[str, str] | None = None     # (tipo, unique_id)
        self.dragging = False
        self.setMinimumSize(360, 360)
        self.setMouseTracking(True)

    # --- coordinate ---
    def scale(self) -> float:
        if self.audio_map is None:
            return 1.0
        return min((self.width() - 20) / float(self.audio_map["width"]), (self.height() - 20) / float(self.audio_map["height"]))

    def to_screen(self, x: float, y: float) -> QPointF:
        factor = self.scale()
        return QPointF(10 + x * factor, 10 + y * factor)

    def to_map(self, point: QPointF) -> tuple[float, float]:
        factor = self.scale()
        x = min(float(self.audio_map["width"]), max(0.0, (point.x() - 10) / factor))
        y = min(float(self.audio_map["height"]), max(0.0, (point.y() - 10) / factor))
        return x, y

    def item_at(self, point: QPointF) -> tuple[str, dict] | None:
        if self.audio_map is None:
            return None
        for kind in reversed(KINDS):
            for item in reversed(self.audio_map[kind]):
                center = self.to_screen(item["x"], item["y"])
                if math.hypot(center.x() - point.x(), center.y() - point.y()) <= PICK_RADIUS:
                    return kind, item
        return None

    def selected_item(self) -> tuple[str, dict] | None:
        if self.audio_map is None or self.selected is None:
            return None
        kind, unique_id = self.selected
        for item in self.audio_map[kind]:
            if item["unique_id"] == unique_id:
                return kind, item
        return None

    # --- mouse ---
    def mousePressEvent(self, event) -> None:
        found = self.item_at(event.position())
        self.selected = (found[0], found[1]["unique_id"]) if found is not None else None
        self.dragging = found is not None
        self.selection_changed.emit()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.dragging == False or self.audio_map is None:
            return
        found = self.selected_item()
        if found is None:
            return
        x, y = self.to_map(event.position())
        found[1]["x"] = x
        found[1]["y"] = y
        if found[0] == "objects":
            found[1]["home_x"] = x
            found[1]["home_y"] = y
        self.edited.emit()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        self.dragging = False

    # --- disegno ---
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#202225"))
        if self.audio_map is None:
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Nessuna mappa")
            return
        corner = self.to_screen(self.audio_map["width"], self.audio_map["height"])
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.setBrush(QColor("#2a2d31"))
        painter.drawRect(QRectF(10, 10, corner.x() - 10, corner.y() - 10))
        for item in self.audio_map["filters"]:
            self._paint_filter(painter, item)
        for item in self.audio_map["marks"]:
            self._paint_mark(painter, item)
        for item in self.audio_map["objects"]:
            self._paint_object(painter, item)

    def _is_selected(self, kind: str, item: dict) -> bool:
        return self.selected == (kind, item["unique_id"])

    def _paint_mark(self, painter: QPainter, item: dict) -> None:
        center = self.to_screen(item["x"], item["y"])
        radius = 6.0 + item.get("gravity", 1.0) * 2.0
        painter.setBrush(QColor(80, 140, 220, 90))
        painter.setPen(QPen(QColor("#ffd24a") if self._is_selected("marks", item) else QColor("#5a9bd8"), 2))
        painter.drawEllipse(center, radius, radius)
        painter.setPen(QColor("#dddddd"))
        painter.drawText(QPointF(center.x() + radius + 3, center.y() + 4), item["name"])

    def _paint_filter(self, painter: QPainter, item: dict) -> None:
        center = self.to_screen(item["x"], item["y"])
        angle = math.radians(item["angle"])
        length = 40.0 + item.get("width", 0.0) * self.scale() / 2.0
        direction = QPointF(math.cos(angle), math.sin(angle))
        painter.setPen(QPen(QColor("#ffd24a") if self._is_selected("filters", item) else QColor("#d8803a"), 2))
        painter.drawLine(QPointF(center.x() - direction.x() * length, center.y() - direction.y() * length),
                         QPointF(center.x() + direction.x() * length, center.y() + direction.y() * length))
        painter.drawLine(center, QPointF(center.x() - direction.y() * 12, center.y() + direction.x() * 12))
        painter.setPen(QColor("#dddddd"))
        painter.drawText(QPointF(center.x() + 6, center.y() - 6), item["name"])

    def _paint_object(self, painter: QPainter, item: dict) -> None:
        center = self.to_screen(item["x"], item["y"])
        if item.get("spread", 0.0) > 0:
            spread = item["spread"] * self.scale()
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 80), 1, Qt.DashLine))
            painter.drawEllipse(center, spread, spread)
        painter.setBrush(QColor(COLOR_VALUES.get(item.get("color", "none"), "#e8e8e8")))
        painter.setPen(QPen(QColor("#ffd24a") if self._is_selected("objects", item) else QColor("#000000"), 2))
        painter.drawEllipse(center, 8, 8)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QPointF(center.x() + 11, center.y() + 4), item["name"])


class AudioMapEditor(QWidget):
    changed = Signal()

    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self.setWindowTitle("Audio Map Editor")
        self.resize(900, 560)
        self._loading = False
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.map_box = QComboBox()
        self.map_box.currentIndexChanged.connect(self._map_chosen)
        self.new_map_button = QPushButton("Nuova mappa")
        self.new_map_button.clicked.connect(self.add_map)
        self.delete_map_button = QPushButton("Elimina mappa")
        self.delete_map_button.clicked.connect(self.delete_map)
        self.map_name = QLineEdit()
        self.map_name.editingFinished.connect(self._rename_map)
        top.addWidget(self.map_box, 1)
        top.addWidget(self.map_name, 1)
        top.addWidget(self.new_map_button)
        top.addWidget(self.delete_map_button)
        root.addLayout(top)
        split = QSplitter()
        self.canvas = MapCanvas()
        self.canvas.selection_changed.connect(self._selection_changed)
        self.canvas.edited.connect(self._canvas_edited)
        split.addWidget(self.canvas)
        side = QWidget()
        side_layout = QVBoxLayout(side)
        add_row = QHBoxLayout()
        self.add_buttons = {}
        for kind in KINDS:
            button = QPushButton("+ " + KIND_LABELS[kind])
            button.clicked.connect(lambda checked=False, chosen=kind: self.add_item(chosen))
            add_row.addWidget(button)
            self.add_buttons[kind] = button
        side_layout.addLayout(add_row)
        self.form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(lambda: self._set_field("name", self.name_edit.text()))
        self.x_spin = self._spin(0.0, 100000.0, "x")
        self.y_spin = self._spin(0.0, 100000.0, "y")
        self.gravity_spin = self._spin(0.1, 5.0, "gravity")
        self.shadow_spin = self._spin(0.0, 90.0, "shadow")
        self.angle_spin = self._spin(-360.0, 360.0, "angle")
        self.width_spin = self._spin(0.0, 100000.0, "width")
        self.spread_spin = self._spin(0.0, 100000.0, "spread")
        self.color_box = QComboBox()
        self.color_box.addItems(audiomap.COLORS)
        self.color_box.currentTextChanged.connect(lambda text: self._set_field("color", text))
        self.fields = {"name": self.name_edit, "x": self.x_spin, "y": self.y_spin, "gravity": self.gravity_spin,
                       "shadow": self.shadow_spin, "angle": self.angle_spin, "width": self.width_spin,
                       "spread": self.spread_spin, "color": self.color_box}
        for key, label in (("name", "Nome"), ("x", "X"), ("y", "Y"), ("gravity", "Gravity"), ("shadow", "Shadow °"),
                           ("angle", "Angolo °"), ("width", "Larghezza"), ("spread", "Spread"), ("color", "Colore")):
            self.form.addRow(label, self.fields[key])
        side_layout.addLayout(self.form)
        self.levels_table = QTableWidget(0, 2)
        self.levels_table.setHorizontalHeaderLabels(["Uscita (0 = main)", "dB"])
        self.levels_table.horizontalHeader().setStretchLastSection(True)
        self.levels_table.itemChanged.connect(self._levels_edited)
        side_layout.addWidget(self.levels_table)
        level_row = QHBoxLayout()
        self.add_level_button = QPushButton("+ Uscita")
        self.add_level_button.clicked.connect(self.add_level)
        self.delete_item_button = QPushButton("Elimina elemento")
        self.delete_item_button.clicked.connect(self.delete_item)
        level_row.addWidget(self.add_level_button)
        level_row.addWidget(self.delete_item_button)
        side_layout.addLayout(level_row)
        self.preview = QLabel("")
        self.preview.setWordWrap(True)
        side_layout.addWidget(QLabel("Livelli risultanti (oggetto scelto)"))
        side_layout.addWidget(self.preview)
        split.addWidget(side)
        split.setSizes([560, 340])
        root.addWidget(split, 1)
        self.reload()

    def _spin(self, low: float, high: float, key: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(2)
        spin.valueChanged.connect(lambda value: self._set_field(key, value))
        return spin

    # --- mappe ---
    def maps(self) -> list:
        return self.workspace.patches.setdefault("audio_map", [])

    def current_map(self) -> dict | None:
        index = self.map_box.currentIndex()
        maps = self.maps()
        return maps[index] if 0 <= index < len(maps) else None

    def reload(self, keep_index: int = 0) -> None:
        self._loading = True
        self.map_box.clear()
        for audio_map in self.maps():
            self.map_box.addItem(audio_map["name"])
        if self.map_box.count() > 0:
            self.map_box.setCurrentIndex(min(keep_index, self.map_box.count() - 1))
        self._loading = False
        self._map_chosen()

    def _map_chosen(self) -> None:
        if self._loading == True:
            return
        audio_map = self.current_map()
        self.canvas.audio_map = audio_map
        self.canvas.selected = None
        self.map_name.setText(audio_map["name"] if audio_map is not None else "")
        for button in self.add_buttons.values():
            button.setEnabled(audio_map is not None)
        self._selection_changed()
        self.canvas.update()

    def add_map(self) -> None:
        number = len(self.maps()) + 1
        self.maps().append(audiomap.new_map("Map " + str(number)))
        self._touch()
        self.reload(len(self.maps()) - 1)

    def delete_map(self) -> None:
        index = self.map_box.currentIndex()
        if 0 <= index < len(self.maps()):
            del self.maps()[index]
            self._touch()
            self.reload(0)

    def _rename_map(self) -> None:
        audio_map = self.current_map()
        if audio_map is None or self.map_name.text() == audio_map["name"]:
            return
        audio_map["name"] = self.map_name.text()
        self.map_box.setItemText(self.map_box.currentIndex(), audio_map["name"])
        self._touch()

    # --- elementi ---
    def add_item(self, kind: str) -> None:
        audio_map = self.current_map()
        if audio_map is None:
            return
        center_x = audio_map["width"] / 2.0
        center_y = audio_map["height"] / 2.0
        if kind == "marks":
            item = audiomap.add_mark(audio_map, "Mark " + str(len(audio_map["marks"]) + 1), center_x, center_y,
                                     {0: 0.0})
        elif kind == "filters":
            item = audiomap.add_filter(audio_map, "Filtro " + str(len(audio_map["filters"]) + 1), center_x, center_y)
        else:
            item = audiomap.add_object(audio_map, None, center_x, center_y)
        self.canvas.selected = (kind, item["unique_id"])
        self._touch()
        self._selection_changed()
        self.canvas.update()

    def delete_item(self) -> None:
        found = self.canvas.selected_item()
        audio_map = self.current_map()
        if found is None or audio_map is None:
            return
        audio_map[found[0]].remove(found[1])
        self.canvas.selected = None
        self._touch()
        self._selection_changed()
        self.canvas.update()

    def _selection_changed(self) -> None:
        found = self.canvas.selected_item()
        self._loading = True
        visible = {"mark": ("gravity", "shadow"), "filter": ("angle", "width"), "object": ("spread", "color")}
        kind = None
        if found is not None:
            kind = found[0][:-1]
        shown = set(("name", "x", "y")) if found is not None else set()
        if kind is not None:
            shown.update(visible[kind])
        for key, widget in self.fields.items():
            self.form.setRowVisible(widget, key in shown)
        self.levels_table.setVisible(kind == "mark")
        self.add_level_button.setVisible(kind == "mark")
        self.delete_item_button.setEnabled(found is not None)
        if found is not None:
            item = found[1]
            for key, widget in self.fields.items():
                if key not in shown:
                    continue
                if key == "name":
                    widget.setText(item["name"])
                elif key == "color":
                    widget.setCurrentText(item.get("color", "none"))
                else:
                    widget.setValue(float(item.get(key, 0.0)))
            self._fill_levels(item if kind == "mark" else None)
        self._loading = False
        self._update_preview()

    def _canvas_edited(self) -> None:
        found = self.canvas.selected_item()
        if found is not None:
            self._loading = True
            self.x_spin.setValue(found[1]["x"])
            self.y_spin.setValue(found[1]["y"])
            self._loading = False
        self._touch()
        self._update_preview()

    def _set_field(self, key: str, value) -> None:
        if self._loading == True:
            return
        found = self.canvas.selected_item()
        if found is None:
            return
        item = found[1]
        if key == "gravity":
            value = min(5.0, max(0.1, float(value)))
        item[key] = value
        if found[0] == "objects" and key in ("x", "y"):
            item["home_" + key] = value
        if key == "name":
            item["name"] = str(value)
        self._touch()
        self.canvas.update()
        self._update_preview()

    # --- livelli dei marks ---
    def _fill_levels(self, mark: dict | None) -> None:
        self.levels_table.blockSignals(True)
        self.levels_table.setRowCount(0)
        if mark is not None:
            for output, decibel in sorted(mark["levels"].items()):
                row = self.levels_table.rowCount()
                self.levels_table.insertRow(row)
                self.levels_table.setItem(row, 0, QTableWidgetItem(str(output)))
                self.levels_table.setItem(row, 1, QTableWidgetItem(format_decibel(decibel)))
        self.levels_table.blockSignals(False)

    def add_level(self) -> None:
        found = self.canvas.selected_item()
        if found is None or found[0] != "marks":
            return
        used = set(found[1]["levels"].keys())
        output = 0
        while output in used:
            output = output + 1
        found[1]["levels"][output] = 0.0
        self._fill_levels(found[1])
        self._touch()
        self._update_preview()

    def _levels_edited(self, changed_item) -> None:
        if self._loading == True:
            return
        found = self.canvas.selected_item()
        if found is None or found[0] != "marks":
            return
        levels = {}
        try:
            for row in range(self.levels_table.rowCount()):
                output = int(self.levels_table.item(row, 0).text())
                decibel = parse_decibel(self.levels_table.item(row, 1).text())
                if 0 <= output <= audiomap.OUTPUT_COUNT:
                    levels[output] = decibel
        except ValueError:
            self._fill_levels(found[1])
            return
        found[1]["levels"] = levels
        self._touch()
        self._update_preview()

    def _update_preview(self) -> None:
        found = self.canvas.selected_item()
        audio_map = self.current_map()
        if found is None or audio_map is None or found[0] != "objects":
            self.preview.setText("")
            return
        item = found[1]
        levels = audiomap.object_levels(audio_map, item["x"], item["y"], item.get("spread", 0.0))
        if len(levels) == 0:
            self.preview.setText("(nessun livello definito nei marks)")
            return
        parts = []
        for output in sorted(levels):
            label = "main" if output == 0 else "u" + str(output)
            parts.append("%s %s dB" % (label, format_decibel(levels[output])))
        self.preview.setText("   ".join(parts))

    def _touch(self) -> None:
        self.workspace.modified = True
        self.changed.emit()
