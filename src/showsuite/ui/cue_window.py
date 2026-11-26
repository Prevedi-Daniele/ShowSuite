"""Finestra principale della sezione Cue (stile QLab 5): lista cue, Inspector, cart, impostazioni workspace."""
from __future__ import annotations

import json
import sys

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QKeySequence
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QHeaderView,
                               QInputDialog, QKeySequenceEdit, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
                               QPlainTextEdit, QPushButton, QSpinBox, QTabBar, QTabWidget, QToolBar, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QAbstractItemView, QStackedWidget)

from ..cue.engine import ManualClock, Runtime, SystemClock
from ..cue.model import (CONTINUE_AUTO_CONTINUE, CONTINUE_AUTO_FOLLOW, CONTINUE_NONE, COLORS, CUE_TYPES,
                         DuplicateNumberError, GROUP_TIMELINE, InvalidNumberError, TYPE_CART, TYPE_GROUP, Cue, Workspace)
from ..cue.playback import INFINITE
from ..cue.services import Services
from ..cue.timeutil import format_time, parse_time

CONTINUE_LABELS = ["—", "Auto-continue", "Auto-follow"]
CONTINUE_SYMBOLS = ["", "↧", "⤓"]
TYPE_LABELS = {"audio": "Audio", "mic": "Mic", "video": "Video", "camera": "Camera", "text": "Text", "light": "Light",
               "fade": "Fade", "network": "Network", "midi": "MIDI", "midi file": "MIDI File",
               "timecode": "Timecode", "group": "Group", "start": "Start", "stop": "Stop", "pause": "Pause",
               "load": "Load", "reset": "Reset", "devamp": "Devamp", "goto": "GoTo", "target": "Target",
               "arm": "Arm", "disarm": "Disarm", "wait": "Wait", "memo": "Memo", "script": "Script",
               "list": "Lista", "cart": "Cart"}
GROUP_MODE_LABELS = ["Cue List", "Start first and enter", "Start first", "Timeline", "Start random", "Cart",
                     "Playlist"]
COLOR_RGB = {"none": None, "red": "#7a2a2a", "orange": "#8a5a1f", "green": "#2c6a3a", "blue": "#2a4c7a",
             "purple": "#5a3a7a"}
SECOND_TRIGGER_LABELS = ["Nessuna", "Panic", "Stop", "Hard stop", "Hard stop e riavvia", "Devamp",
                         "Playlist: successivo", "Playlist: precedente"]

STATE_COLORS = {"running": "#1f6f3a", "pre_wait": "#8a6d1f", "paused": "#6b5a1f", "broken": "#7a2a2a",
                "playhead": "#2a4a7a"}


class ParamEditor(QWidget):
    """Editor generico dei parametri specifici del tipo: bool/int/float/str con widget dedicati, resto in JSON."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.cue: Cue | None = None
        self.form = QFormLayout(self)
        self.widgets: dict = {}
        self._loading = False

    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        while self.form.rowCount() > 0:
            self.form.removeRow(0)
        self.widgets = {}
        if cue is not None:
            for key in sorted(cue.params.keys()):
                value = cue.params[key]
                widget = self._make_widget(key, value)
                self.widgets[key] = widget
                self.form.addRow(key.replace("_", " "), widget)
        self._loading = False

    def _make_widget(self, key: str, value):
        if isinstance(value, bool):
            widget = QCheckBox()
            widget.setChecked(value)
            widget.toggled.connect(lambda state, name=key: self._set(name, bool(state)))
        elif isinstance(value, int):
            widget = QSpinBox()
            widget.setRange(-1000000, 1000000)
            widget.setValue(value)
            widget.valueChanged.connect(lambda state, name=key: self._set(name, int(state)))
        elif isinstance(value, float):
            widget = QDoubleSpinBox()
            widget.setDecimals(3)
            widget.setRange(-1000000.0, 1000000.0)
            widget.setValue(value)
            widget.valueChanged.connect(lambda state, name=key: self._set(name, float(state)))
        elif isinstance(value, str):
            widget = QLineEdit(value)
            widget.editingFinished.connect(lambda name=key, field=widget: self._set(name, field.text()))
        else:
            widget = QLineEdit(json.dumps(value, ensure_ascii=False))
            widget.editingFinished.connect(lambda name=key, field=widget: self._set_json(name, field))
        return widget

    def _set(self, key: str, value) -> None:
        if self._loading == True or self.cue is None:
            return
        self.cue.params[key] = value
        self.changed.emit()

    def _set_json(self, key: str, field: QLineEdit) -> None:
        if self._loading == True or self.cue is None:
            return
        try:
            self.cue.params[key] = json.loads(field.text())
            field.setStyleSheet("")
        except ValueError:
            field.setStyleSheet("border: 1px solid #c33;")
            return
        self.changed.emit()


class Inspector(QWidget):
    changed = Signal()

    def __init__(self, workspace: Workspace):
        super().__init__()
        self.workspace = workspace
        self.cue: Cue | None = None
        self._loading = False
        self.tabs = QTabWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.title = QLabel("Nessun cue selezionato")
        self.title.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title)
        layout.addWidget(self.tabs)
        self._build_basics()
        self._build_triggers()
        self.params_editor = ParamEditor()
        self.params_editor.changed.connect(self.changed.emit)
        self.tabs.addTab(self.params_editor, "Parametri")
        from .cue_editors import EnvelopeEditor, LevelsEditor, SliceEditor
        self.media_editors = {"Livelli": LevelsEditor(workspace), "Slice": SliceEditor(),
                              "Envelope": EnvelopeEditor()}
        from .cue_message_editors import FadeEditor, MidiEditor, NetworkEditor
        self.type_editors = {"network": {"Network": NetworkEditor()}, "midi": {"MIDI": MidiEditor()},
                             "fade": {"Fade": FadeEditor()}}
        from .cue_timeline import TimelineEditor
        self.timeline_editor = TimelineEditor()
        self.timeline_editor.changed.connect(self._touch)
        for editor in self.media_editors.values():
            editor.changed.connect(self._touch)
        for group in self.type_editors.values():
            for editor in group.values():
                editor.changed.connect(self._touch)

    @staticmethod
    def _top_aligned(page: QWidget) -> QWidget:
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)
        layout.addStretch(1)
        return holder

    # --- Basics ---
    def _build_basics(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.number = QLineEdit()
        self.number.editingFinished.connect(self._set_number)
        self.number_error = QLabel("")
        self.number_error.setStyleSheet("color: #e66;")
        self.number_error.setFixedHeight(16)
        self.name = QLineEdit()
        self.name.editingFinished.connect(lambda: self._set_attr("name", self.name.text()))
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(60)
        self.notes.textChanged.connect(lambda: self._set_attr("notes", self.notes.toPlainText()))
        self.target = QLineEdit()
        self.target.setPlaceholderText("numero o id del cue target")
        self.target.editingFinished.connect(self._set_target)
        self.pre_wait = QLineEdit()
        self.pre_wait.editingFinished.connect(lambda: self._set_time("pre_wait", self.pre_wait))
        self.duration = QLineEdit()
        self.duration.editingFinished.connect(lambda: self._set_time("duration", self.duration))
        self.post_wait = QLineEdit()
        self.post_wait.editingFinished.connect(lambda: self._set_time("post_wait", self.post_wait))
        self.continue_mode = QComboBox()
        self.continue_mode.addItems(CONTINUE_LABELS)
        self.continue_mode.currentIndexChanged.connect(lambda index: self._set_attr("continue_mode", index))
        self.color = QComboBox()
        self.color.addItems(COLORS)
        self.color.currentTextChanged.connect(lambda text: self._set_attr("color", text))
        self.color_condition = QComboBox()
        self.color_condition.addItems(["always", "before_action", "after_action"])
        self.color_condition.currentTextChanged.connect(lambda text: self._set_attr("color_condition", text))
        self.armed = QCheckBox("Armato")
        self.armed.toggled.connect(lambda state: self._set_attr("armed", bool(state)))
        self.flagged = QCheckBox("Flag")
        self.flagged.toggled.connect(lambda state: self._set_attr("flagged", bool(state)))
        self.auto_load = QCheckBox("Auto-load")
        self.auto_load.toggled.connect(lambda state: self._set_attr("auto_load", bool(state)))
        self.group_mode = QComboBox()
        self.group_mode.addItems(GROUP_MODE_LABELS)
        self.group_mode.currentIndexChanged.connect(self._set_group_mode)
        form.addRow("Numero", self.number)
        form.addRow("", self.number_error)
        form.addRow("Nome", self.name)
        form.addRow("Modo Group", self.group_mode)
        form.addRow("Target", self.target)
        form.addRow("Pre-wait", self.pre_wait)
        form.addRow("Durata", self.duration)
        form.addRow("Post-wait", self.post_wait)
        form.addRow("Continue", self.continue_mode)
        flags = QHBoxLayout()
        flags.addWidget(self.armed)
        flags.addWidget(self.flagged)
        flags.addWidget(self.auto_load)
        form.addRow(flags)
        form.addRow("Colore", self.color)
        form.addRow("Condizione colore", self.color_condition)
        form.addRow("Note", self.notes)
        self.tabs.addTab(self._top_aligned(page), "Basics")

    def _build_triggers(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.hotkey = QKeySequenceEdit()
        self.hotkey.editingFinished.connect(self._set_hotkey)
        self.midi_trigger = QLineEdit()
        self.midi_trigger.setPlaceholderText("note_on canale(0=ws,-1=any) byte1 byte2  es: note_on 0 60 any")
        self.midi_trigger.editingFinished.connect(self._set_midi_trigger)
        self.wall_clock = QLineEdit()
        self.wall_clock.setPlaceholderText("hh:mm:ss  [giorni 0-6 separati da virgola]")
        self.wall_clock.editingFinished.connect(self._set_wall_clock)
        self.timecode = QLineEdit()
        self.timecode.setPlaceholderText("h:m:s:f  (richiede sync timecode sulla lista)")
        self.timecode.editingFinished.connect(self._set_timecode)
        self.second_trigger = QComboBox()
        self.second_trigger.addItems(SECOND_TRIGGER_LABELS)
        self.second_trigger.currentIndexChanged.connect(lambda index: self._set_attr("second_trigger_action", index))
        self.on_release = QCheckBox("Il rilascio vale come secondo trigger")
        self.on_release.toggled.connect(lambda state: self._set_attr("second_trigger_on_release", bool(state)))
        self.fade_stop_mode = QComboBox()
        self.fade_stop_mode.addItems(["Off", "Peers", "Lista/Cart", "Tutti"])
        self.fade_stop_mode.currentIndexChanged.connect(lambda index: self._set_dict("fade_and_stop_others", "mode", index))
        self.fade_stop_time = QDoubleSpinBox()
        self.fade_stop_time.setRange(0, 3600)
        self.fade_stop_time.valueChanged.connect(lambda value: self._set_dict("fade_and_stop_others", "time", value))
        self.duck_enabled = QCheckBox("Duck/boost altri cue")
        self.duck_enabled.toggled.connect(lambda state: self._set_dict("duck_others", "enabled", bool(state)))
        self.duck_level = QDoubleSpinBox()
        self.duck_level.setRange(-120, 12)
        self.duck_level.valueChanged.connect(lambda value: self._set_dict("duck_others", "level", value))
        form.addRow("Hotkey", self.hotkey)
        form.addRow("MIDI", self.midi_trigger)
        form.addRow("Wall clock", self.wall_clock)
        form.addRow("Timecode", self.timecode)
        form.addRow("Secondo trigger", self.second_trigger)
        form.addRow(self.on_release)
        form.addRow("Fade & stop altri", self.fade_stop_mode)
        form.addRow("Tempo fade & stop", self.fade_stop_time)
        form.addRow(self.duck_enabled)
        form.addRow("Livello duck (dB)", self.duck_level)
        self.tabs.addTab(self._top_aligned(page), "Triggers")

    # --- caricamento ---
    def load(self, cue: Cue | None) -> None:
        self._loading = True
        self.cue = cue
        if cue is None:
            self.title.setText("Nessun cue selezionato")
            self.params_editor.load(None)
            while self.tabs.count() > 3:
                self.tabs.removeTab(3)
            self._loading = False
            return
        self.title.setText("%s — %s" % (TYPE_LABELS.get(cue.cue_type, cue.cue_type), cue.display_name(self.workspace)))
        self.number.setText(cue.number)
        self.number_error.setText("")
        self.name.setText(cue.name)
        self.name.setPlaceholderText(cue.default_name(self.workspace))
        self.notes.setPlainText(cue.notes)
        target = self.workspace.find_target(cue)
        self.target.setText(cue.target_number if cue.target_number != "" else (target.number if target else ""))
        self.target.setEnabled(cue.has_cue_target())
        self.pre_wait.setText(format_time(cue.pre_wait))
        self.duration.setText(format_time(cue.duration))
        self.duration.setEnabled(cue.allows_editing_duration())
        self.post_wait.setText(format_time(cue.post_wait))
        self.continue_mode.setCurrentIndex(cue.continue_mode)
        self.color.setCurrentText(cue.color)
        self.color_condition.setCurrentText(cue.color_condition)
        self.armed.setChecked(cue.armed)
        self.flagged.setChecked(cue.flagged)
        self.auto_load.setChecked(cue.auto_load)
        self.group_mode.setEnabled(cue.cue_type == TYPE_GROUP)
        if cue.cue_type == TYPE_GROUP:
            self.group_mode.setCurrentIndex(cue.group_mode())
        triggers = cue.triggers
        self.hotkey.setKeySequence(QKeySequence(triggers.get("hotkey") or ""))
        midi = triggers.get("midi")
        self.midi_trigger.setText("" if not midi else "%s %s %s %s" % (midi.get("status", "note_on"),
                                  midi.get("channel", 0), midi.get("byte1", "any"), midi.get("byte2", "any")))
        wall = triggers.get("wall_clock")
        self.wall_clock.setText("" if not wall else wall.get("time", "") + (
            "  " + ",".join(str(day) for day in wall.get("days", [])) if wall.get("days") else ""))
        timecode = triggers.get("timecode")
        self.timecode.setText("" if not timecode else str(timecode.get("time", "")))
        self.second_trigger.setCurrentIndex(cue.second_trigger_action)
        self.on_release.setChecked(cue.second_trigger_on_release)
        self.fade_stop_mode.setCurrentIndex(int(cue.fade_and_stop_others.get("mode", 0)))
        self.fade_stop_time.setValue(float(cue.fade_and_stop_others.get("time", 0.0)))
        self.duck_enabled.setChecked(bool(cue.duck_others.get("enabled", False)))
        self.duck_level.setValue(float(cue.duck_others.get("level", -12.0)))
        self.params_editor.load(cue)
        self._show_media_editors(cue)
        self._loading = False

    def _show_media_editors(self, cue: Cue) -> None:
        while self.tabs.count() > 3:
            self.tabs.removeTab(3)
        if cue.cue_type == "audio":
            for title, editor in self.media_editors.items():
                editor.load(cue)
                self.tabs.addTab(editor, title)
        if cue.cue_type == "group" and cue.group_mode() == GROUP_TIMELINE:
            self.timeline_editor.load(cue)
            self.tabs.addTab(self.timeline_editor, "Timeline")
        for title, editor in self.type_editors.get(cue.cue_type, {}).items():
            editor.load(cue)
            self.tabs.addTab(self._top_aligned(editor) if title != "Fade" else editor, title)

    # --- scrittura ---
    def _touch(self) -> None:
        self.workspace.modified = True
        self.changed.emit()

    def _set_attr(self, name: str, value) -> None:
        if self._loading == True or self.cue is None:
            return
        setattr(self.cue, name, value)
        self._touch()

    def _set_dict(self, attribute: str, key: str, value) -> None:
        if self._loading == True or self.cue is None:
            return
        getattr(self.cue, attribute)[key] = value
        self._touch()

    def _set_number(self) -> None:
        if self._loading == True or self.cue is None:
            return
        try:
            self.workspace.set_number(self.cue, self.number.text())
            self.number_error.setText("")
        except (DuplicateNumberError, InvalidNumberError) as problem:
            self.number_error.setText(str(problem))
            return
        self._touch()

    def _set_time(self, name: str, field: QLineEdit) -> None:
        if self._loading == True or self.cue is None:
            return
        try:
            setattr(self.cue, name, max(0.0, parse_time(field.text())))
        except ValueError:
            field.setStyleSheet("border: 1px solid #c33;")
            return
        field.setStyleSheet("")
        field.setText(format_time(getattr(self.cue, name)))
        self._touch()

    def _set_target(self) -> None:
        if self._loading == True or self.cue is None:
            return
        text = self.target.text().strip()
        found = self.workspace.find_by_number(text) or self.workspace.find_by_id(text)
        if found is None and text != "":
            self.target.setStyleSheet("border: 1px solid #c33;")
            return
        self.target.setStyleSheet("")
        self.cue.target_id = found.unique_id if found is not None else ""
        self.cue.target_number = ""
        self._touch()

    def _set_group_mode(self, index: int) -> None:
        if self._loading == True or self.cue is None or self.cue.cue_type != TYPE_GROUP:
            return
        self.cue.params["group_mode"] = index
        self._touch()

    def _set_hotkey(self) -> None:
        if self._loading == True or self.cue is None:
            return
        text = self.hotkey.keySequence().toString()
        self.cue.triggers["hotkey"] = text if text != "" else None
        self._touch()

    def _set_midi_trigger(self) -> None:
        if self._loading == True or self.cue is None:
            return
        parts = self.midi_trigger.text().split()
        if len(parts) == 0:
            self.cue.triggers["midi"] = None
        elif len(parts) == 4:
            self.cue.triggers["midi"] = {"status": parts[0], "channel": int(parts[1]), "byte1": parts[2],
                                         "byte2": parts[3]}
        else:
            self.midi_trigger.setStyleSheet("border: 1px solid #c33;")
            return
        self.midi_trigger.setStyleSheet("")
        self._touch()

    def _set_wall_clock(self) -> None:
        if self._loading == True or self.cue is None:
            return
        parts = self.wall_clock.text().split()
        if len(parts) == 0:
            self.cue.triggers["wall_clock"] = None
        else:
            days = [int(day) for day in parts[1].split(",")] if len(parts) > 1 else []
            self.cue.triggers["wall_clock"] = {"time": parts[0], "days": days}
        self._touch()

    def _set_timecode(self) -> None:
        if self._loading == True or self.cue is None:
            return
        text = self.timecode.text().strip()
        self.cue.triggers["timecode"] = {"time": text} if text != "" else None
        self._touch()


class CartView(QWidget):
    """Griglia di pulsanti per un Cart: un clic avvia il cue (senza playhead)."""
    cue_clicked = Signal(object)

    def __init__(self, runtime: Runtime):
        super().__init__()
        self.runtime = runtime
        self.cart: Cue | None = None
        self.grid = QGridLayout(self)
        self.buttons: dict = {}

    def load(self, cart: Cue) -> None:
        self.cart = cart
        while self.grid.count() > 0:
            item = self.grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.buttons = {}
        rows = int(cart.params["rows"])
        columns = int(cart.params["columns"])
        for child in cart.children:
            button = QPushButton("%s\n%s" % (child.number, child.display_name(self.runtime.workspace)))
            button.setMinimumHeight(54)
            button.clicked.connect(lambda checked=False, cue=child: self.cue_clicked.emit(cue))
            self.grid.addWidget(button, child.cart_row - 1, child.cart_column - 1)
            self.buttons[child.unique_id] = button
        for row in range(rows):
            self.grid.setRowStretch(row, 1)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)

    def refresh(self) -> None:
        for identifier, button in self.buttons.items():
            cue = self.runtime.workspace.find_by_id(identifier)
            if cue is None:
                continue
            running = self.runtime.is_active(cue)
            button.setStyleSheet("background: %s;" % (STATE_COLORS["running"] if running else "#33363b"))


class SettingsDialog(QDialog):
    """Impostazioni del workspace (General, OSC, MIDI/MSC, Audition/Override): editor generico dei campi."""

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni workspace")
        self.workspace = workspace
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        groups = {"Generali": ["min_go_time", "key_up", "panic_duration", "auto_number", "auto_number_increment",
                               "auto_load_default", "lock_playhead_to_selection", "start_cue_on_open",
                               "prompt_cue_on_close", "copy_media", "autosave_seconds", "always_audition",
                               "max_volume", "min_volume", "display_size"],
                  "OSC": ["osc_access", "osc_port", "osc_reply_port", "osc_plain_port"],
                  "MIDI / MSC": ["midi_channel", "use_msc", "msc_device_id", "use_musical_midi"]}
        self.editors: dict = {}
        for title, keys in groups.items():
            page = QWidget()
            form = QFormLayout(page)
            for key in keys:
                value = workspace.settings[key]
                editor = self._editor_for(value)
                self.editors[key] = editor
                form.addRow(key.replace("_", " "), editor)
            tabs.addTab(page, title)
        passcodes = QWidget()
        self.passcode_edit = QPlainTextEdit(json.dumps(workspace.settings["passcodes"], indent=1))
        QVBoxLayout(passcodes).addWidget(self.passcode_edit)
        tabs.addTab(passcodes, "Passcode OSC")
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _editor_for(self, value):
        if isinstance(value, bool):
            widget = QCheckBox()
            widget.setChecked(value)
        elif isinstance(value, int):
            widget = QSpinBox()
            widget.setRange(-1000000, 1000000)
            widget.setValue(value)
        elif isinstance(value, float):
            widget = QDoubleSpinBox()
            widget.setRange(-1000.0, 100000.0)
            widget.setValue(value)
        else:
            widget = QLineEdit(str(value))
        return widget

    def apply(self) -> None:
        for key, editor in self.editors.items():
            if isinstance(editor, QCheckBox):
                self.workspace.settings[key] = editor.isChecked()
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)):
                self.workspace.settings[key] = editor.value()
            else:
                self.workspace.settings[key] = editor.text()
        try:
            self.workspace.settings["passcodes"] = json.loads(self.passcode_edit.toPlainText())
        except ValueError:
            pass
        self.workspace.modified = True


class CueWindow(QMainWindow):
    def __init__(self, workspace: Workspace | None = None, runtime: Runtime | None = None, services_options: dict | None = None):
        super().__init__()
        self.workspace = workspace if workspace is not None else Workspace()
        self.runtime = runtime if runtime is not None else Runtime(self.workspace, SystemClock(), check_files=True)
        self.tool_windows: dict = {}
        self.services_options = services_options if services_options is not None else {}
        self.services = Services(self.runtime, **self.services_options)
        self.setWindowTitle("ShowSuite Cue")
        self.resize(1280, 760)
        self._items: dict = {}
        self._building = False
        self.list_tabs = QTabBar()
        self.list_tabs.currentChanged.connect(self._list_tab_changed)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(9)
        self.tree.setHeaderLabels(["", "N.", "Nome", "Target", "Pre-wait", "Durata", "Post-wait", "Cont.", "Trigger"])
        header = self.tree.header()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        for column in (0, 1, 3, 4, 5, 6, 7, 8):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._selection_changed)
        self.tree.itemDoubleClicked.connect(lambda item, column: self.runtime.start_cue(self._cue_of(item)))
        self.tree.model().rowsMoved.connect(self._rows_moved)
        self.cart_view = CartView(self.runtime)
        self.cart_view.cue_clicked.connect(lambda cue: self.runtime.start_cue(cue, origin="trigger"))
        self.stack = QStackedWidget()
        self.stack.addWidget(self.tree)
        self.stack.addWidget(self.cart_view)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_tabs)
        layout.addWidget(self.stack)
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)
        self.inspector = Inspector(self.workspace)
        self.inspector.changed.connect(self.refresh_tree)
        dock = QDockWidget("Inspector", self)
        dock.setWidget(self.inspector)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self._build_toolbar()
        self._build_menu()
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self.refresh_tabs()
        self.refresh_tree()

    # --- barra e menu ---
    def _build_toolbar(self) -> None:
        bar = QToolBar("Principale")
        bar.setMovable(False)
        self.addToolBar(bar)
        self.go_action = QAction("GO", self)
        self.go_action.triggered.connect(lambda: self.runtime.go())
        self.preview_action = QAction("Preview", self)
        self.preview_action.triggered.connect(lambda: self.runtime.preview())
        self.pause_action = QAction("Pause all", self)
        self.pause_action.triggered.connect(self.runtime.pause_all)
        self.resume_action = QAction("Resume all", self)
        self.resume_action.triggered.connect(self.runtime.resume_all)
        self.panic_action = QAction("Panic", self)
        self.panic_action.triggered.connect(self.runtime.panic_all)
        self.reset_action = QAction("Reset", self)
        self.reset_action.triggered.connect(self._reset)
        for action in (self.go_action, self.preview_action, self.pause_action, self.resume_action,
                       self.panic_action, self.reset_action):
            bar.addAction(action)
        bar.addSeparator()
        add_button = QPushButton("+ Nuovo cue")
        menu = QMenu(add_button)
        for cue_type in CUE_TYPES:
            action = menu.addAction(TYPE_LABELS.get(cue_type, cue_type))
            action.triggered.connect(lambda checked=False, kind=cue_type: self.add_cue(kind))
        add_button.setMenu(menu)
        bar.addWidget(add_button)
        delete_action = QAction("Elimina", self)
        delete_action.triggered.connect(self.delete_selected)
        bar.addAction(delete_action)
        group_action = QAction("Raggruppa", self)
        group_action.triggered.connect(self.group_selected)
        bar.addAction(group_action)
        bar.addSeparator()
        self.show_mode_action = QAction("Show mode", self)
        self.show_mode_action.setCheckable(True)
        self.show_mode_action.toggled.connect(self.set_show_mode)
        bar.addAction(self.show_mode_action)
        self.go_action.setShortcut(QKeySequence(Qt.Key_Space))
        self.panic_action.setShortcut(QKeySequence(Qt.Key_Escape))

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Nuovo", self.new_workspace)
        file_menu.addAction("Apri…", self.open_workspace)
        file_menu.addAction("Salva", self.save_workspace)
        file_menu.addAction("Salva con nome…", lambda: self.save_workspace(ask=True))
        file_menu.addAction("Impostazioni workspace…", self.open_settings)
        file_menu.addAction("Patch…", self.open_patches)
        view_menu = self.menuBar().addMenu("Vista")
        view_menu.addAction("Active Cues", lambda: self._show_tool("active"))
        view_menu.addAction("Avvisi", lambda: self._show_tool("warnings"))
        view_menu.addAction("Light Dashboard", self.open_light_dashboard)
        edit_menu = self.menuBar().addMenu("Modifica")
        edit_menu.addAction("Annulla", self.undo)
        edit_menu.addAction("Ripeti", self.redo)
        edit_menu.addAction("Duplica", self.duplicate_selected)
        edit_menu.addAction("Rinumera selezionati…", self.renumber_selected)
        edit_menu.addAction("Nuova lista", lambda: self.add_list(False))
        edit_menu.addAction("Nuovo cart", lambda: self.add_list(True))

    # --- elenco ---
    def refresh_tabs(self) -> None:
        self._building = True
        while self.list_tabs.count() > 0:
            self.list_tabs.removeTab(0)
        for container in self.workspace.lists:
            self.list_tabs.addTab(("▦ " if container.cue_type == TYPE_CART else "") + container.display_name())
        active = self.workspace.lists.index(self.workspace.active_list())
        self.list_tabs.setCurrentIndex(active)
        self._building = False

    def _list_tab_changed(self, index: int) -> None:
        if self._building == True or index < 0:
            return
        self.workspace.active_list_id = self.workspace.lists[index].unique_id
        self.refresh_tree()

    def _cue_of(self, item: QTreeWidgetItem) -> Cue | None:
        return self.workspace.find_by_id(item.data(0, Qt.UserRole))

    def refresh_tree(self) -> None:
        self._building = True
        selected = [cue.unique_id for cue in self.selected_cues()]
        container = self.workspace.active_list()
        self.tree.clear()
        self._items = {}
        if container.cue_type == TYPE_CART:
            self.cart_view.load(container)
            self.stack.setCurrentWidget(self.cart_view)
        else:
            self.stack.setCurrentWidget(self.tree)
            self._add_items(self.tree.invisibleRootItem(), container)
            self.tree.expandAll()
        for identifier in selected:
            item = self._items.get(identifier)
            if item is not None:
                item.setSelected(True)
        self._building = False
        self.update_status()

    def _add_items(self, parent_item, parent_cue: Cue) -> None:
        for cue in parent_cue.children:
            item = QTreeWidgetItem(parent_item)
            item.setData(0, Qt.UserRole, cue.unique_id)
            self._items[cue.unique_id] = item
            self._fill_item(item, cue)
            self._add_items(item, cue)

    def _fill_item(self, item: QTreeWidgetItem, cue: Cue) -> None:
        workspace = self.workspace
        target = self.runtime.resolve_target(cue)
        marks = ("⚑" if cue.flagged else "") + ("" if cue.armed else "∅")
        item.setText(0, marks)
        item.setText(1, cue.number)
        label = ("▸ " if cue.cue_type == TYPE_GROUP else "") + cue.display_name(workspace)
        item.setText(2, "[%s] %s" % (TYPE_LABELS.get(cue.cue_type, cue.cue_type), label))
        item.setText(3, target.display_name(workspace) if target is not None else "")
        item.setText(4, format_time(cue.pre_wait) if cue.pre_wait > 0 else "")
        item.setText(5, format_time(cue.duration) if cue.allows_editing_duration() else "")
        item.setText(6, format_time(cue.post_wait) if cue.post_wait > 0 else "")
        item.setText(7, CONTINUE_SYMBOLS[cue.continue_mode])
        triggers = [name for name, value in cue.triggers.items() if value]
        item.setText(8, ", ".join(triggers))
        base = COLOR_RGB.get(self.runtime.current_color(cue))
        item.setBackground(2, QBrush(QColor(base)) if base is not None else QBrush())
        font = item.font(2)
        font.setItalic(cue.armed == False)
        item.setFont(2, font)
        broken = self.runtime.broken_reason(cue)
        item.setToolTip(2, broken)

    def selected_cues(self) -> list[Cue]:
        cues = []
        for item in self.tree.selectedItems():
            cue = self._cue_of(item)
            if cue is not None:
                cues.append(cue)
        return cues

    def _selection_changed(self) -> None:
        if self._building == True:
            return
        cues = self.selected_cues()
        self.runtime.set_selection(cues)
        self.inspector.load(cues[0] if len(cues) == 1 else None)

    # --- aggiornamento periodico ---
    def _tick(self) -> None:
        self.runtime.update()
        self.services.tick()
        self.paint_states()
        if self.inspector.timeline_editor.isVisible() == True:
            self.inspector.timeline_editor.refresh_playhead(self.runtime)

    def start_updates(self) -> None:
        self.services.start()
        self.timer.start()

    def closeEvent(self, event) -> None:
        if hasattr(self, "timer") == True:
            self.timer.stop()
        if hasattr(self, "services") == True:
            self.services.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        sequence = QKeySequence(event.keyCombination()).toString()
        if event.isAutoRepeat() == False and self.services.triggers.key_event(sequence, True):
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.isAutoRepeat() == False:
            self.services.triggers.key_event(QKeySequence(event.keyCombination()).toString(), False)
        super().keyReleaseEvent(event)

    def paint_states(self) -> None:
        playhead = self.runtime.playhead()
        for identifier, item in self._items.items():
            cue = self.workspace.find_by_id(identifier)
            if cue is None:
                continue
            status = self.runtime.status(cue)
            color = None
            if status["broken"] == True:
                color = STATE_COLORS["broken"]
            if status["paused"] == True:
                color = STATE_COLORS["paused"]
            elif status["pre_wait_running"] == True:
                color = STATE_COLORS["pre_wait"]
            elif status["running"] == True:
                color = STATE_COLORS["running"]
            elif playhead is not None and playhead.unique_id == identifier:
                color = STATE_COLORS["playhead"]
            brush = QBrush(QColor(color)) if color is not None else QBrush()
            item.setBackground(0, brush)
            item.setBackground(1, brush)
            progress = ""
            if status["pre_wait_running"] == True:
                progress = "pre " + format_time(status["pre_wait_elapsed"])
            elif status["running"] == True:
                total = status["action_duration"]
                progress = format_time(status["action_elapsed"]) + (
                    "" if total == INFINITE or total == 0 else " / " + format_time(total))
            item.setText(5, progress if progress != "" else (
                format_time(cue.duration) if cue.allows_editing_duration() else ""))
        self.cart_view.refresh()
        self.update_status()

    def update_status(self) -> None:
        playhead = self.runtime.playhead()
        running = len(self.runtime.active_cues())
        text = "Playhead: " + (playhead.standby_display(self.workspace) if playhead is not None else "—")
        text = text + "   In esecuzione: %d" % running
        if self.workspace.settings.get("show_mode", False) == True:
            text = text + "   [SHOW MODE]"
        self.status_label.setText(text)

    # --- operazioni sul documento ---
    def _mutate(self) -> None:
        self.workspace.push_undo()

    def add_cue(self, cue_type: str) -> None:
        if self.workspace.settings.get("show_mode", False) == True:
            return
        self._mutate()
        container = self.workspace.active_list()
        parent = container
        index = None
        selected = self.selected_cues()
        if len(selected) > 0:
            anchor = selected[-1]
            if anchor.cue_type == TYPE_GROUP and cue_type != TYPE_GROUP and container.cue_type != TYPE_CART:
                parent = anchor
            else:
                parent = anchor.parent
                index = parent.children.index(anchor) + 1
        if container.cue_type == TYPE_CART and cue_type == TYPE_GROUP:
            return
        cue = self.workspace.new_cue(cue_type, parent=parent, index=index)
        if cue.has_cue_target() == True and len(selected) == 1 and selected[0] is not cue:
            cue.target_id = selected[0].unique_id
        if self.runtime.playhead(container) is None and container.cue_type == "list":
            self.runtime.set_playhead(cue, container)
        self.refresh_tree()
        item = self._items.get(cue.unique_id)
        if item is not None:
            self.tree.clearSelection()
            item.setSelected(True)

    def delete_selected(self) -> None:
        if self.workspace.settings.get("show_mode", False) == True:
            return
        cues = self.selected_cues()
        if len(cues) == 0:
            return
        self._mutate()
        for cue in cues:
            if cue.parent is not None and self.workspace.find_by_id(cue.unique_id) is not None:
                self.runtime.stop_cue(cue, hard=True)
                self.workspace.delete_cue(cue)
        self.runtime.ensure_playheads()
        self.refresh_tree()
        self.inspector.load(None)

    def group_selected(self) -> None:
        cues = self.selected_cues()
        if len(cues) < 1 or self.workspace.settings.get("show_mode", False) == True:
            return
        try:
            self._mutate()
            self.workspace.make_group(cues)
        except ValueError as problem:
            QMessageBox.warning(self, "Raggruppa", str(problem))
            return
        self.refresh_tree()

    def duplicate_selected(self) -> None:
        cues = self.selected_cues()
        if len(cues) == 0:
            return
        self._mutate()
        for cue in cues:
            self.workspace.duplicate_cue(cue)
        self.refresh_tree()

    def renumber_selected(self) -> None:
        cues = self.selected_cues()
        if len(cues) == 0:
            return
        start, accepted = QInputDialog.getDouble(self, "Rinumera", "Primo numero:", 1.0, 0.0, 100000.0, 2)
        if accepted == False:
            return
        self._mutate()
        self.workspace.renumber(cues, start, 1.0)
        self.refresh_tree()

    def add_list(self, cart: bool) -> None:
        self._mutate()
        container = self.workspace.new_list("Cue Cart" if cart else "Lista %d" % (len(self.workspace.lists) + 1), cart)
        self.runtime.ensure_playheads()
        self.workspace.active_list_id = container.unique_id
        self.refresh_tabs()
        self.refresh_tree()

    def _rows_moved(self, *arguments) -> None:
        if self._building == True:
            return
        QTimer.singleShot(0, self._sync_order_from_tree)

    def _sync_order_from_tree(self) -> None:
        """Dopo un drag & drop ricostruisce la gerarchia dei cue dallo stato dell'albero."""
        container = self.workspace.active_list()
        self._mutate()

        def rebuild(parent_item, parent_cue: Cue) -> None:
            ordered = []
            for index in range(parent_item.childCount()):
                child_item = parent_item.child(index)
                cue = self.workspace.find_by_id(child_item.data(0, Qt.UserRole))
                if cue is not None:
                    ordered.append((cue, child_item))
            parent_cue.children = [cue for cue, item in ordered]
            for cue, item in ordered:
                cue.parent = parent_cue
                rebuild(item, cue)

        rebuild(self.tree.invisibleRootItem(), container)
        self.workspace.modified = True
        self.refresh_tree()

    def undo(self) -> None:
        if self.workspace.undo() == True:
            self.runtime.reset_workspace(load=False)
            self.refresh_tabs()
            self.refresh_tree()

    def redo(self) -> None:
        if self.workspace.redo() == True:
            self.runtime.reset_workspace(load=False)
            self.refresh_tabs()
            self.refresh_tree()

    def _reset(self) -> None:
        self.runtime.reset_workspace()
        self.refresh_tree()

    def set_show_mode(self, enabled: bool) -> None:
        self.workspace.settings["show_mode"] = bool(enabled)
        self.inspector.setEnabled(enabled == False)
        self.tree.setDragDropMode(QAbstractItemView.NoDragDrop if enabled else QAbstractItemView.InternalMove)
        self.update_status()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.workspace, self)
        if dialog.exec() == QDialog.Accepted:
            dialog.apply()
            if self.services.osc_from_workspace == True:
                self.services.restart_osc()
                for message in self.services.errors:
                    self.status_label.setText(message)

    def _show_tool(self, kind: str) -> None:
        from .cue_active import ActiveCuesWindow, WarningsWindow
        window_class = ActiveCuesWindow if kind == "active" else WarningsWindow
        existing = self.tool_windows.get(kind)
        if existing is None or existing.runtime is not self.runtime:
            existing = window_class(self.runtime)
            self.tool_windows[kind] = existing
        existing.show()
        existing.raise_()

    def open_light_dashboard(self) -> None:
        bridge = self.runtime.light_bridge
        if bridge is None:
            self.status_label.setText("Light non collegato: avvia Cue con un progetto Light (--light) o un bridge OSC")
            return
        from .cue_light_dashboard import LightDashboardWindow
        existing = self.tool_windows.get("light")
        if existing is None or existing.bridge is not bridge:
            existing = LightDashboardWindow(bridge)
            self.tool_windows["light"] = existing
        existing.show()
        existing.raise_()

    def open_patches(self) -> None:
        from .cue_patch_dialog import PatchDialog
        dialog = PatchDialog(self.workspace, self)
        if dialog.exec() == QDialog.Accepted:
            dialog.apply()

    # --- file ---
    def new_workspace(self) -> None:
        self._replace_workspace(Workspace())

    def open_workspace(self) -> None:
        path, selected = QFileDialog.getOpenFileName(self, "Apri workspace", "", "ShowSuite Cue (*.showcue)")
        if path != "":
            self._replace_workspace(Workspace.load(path))

    def save_workspace(self, ask: bool = False) -> None:
        path = self.workspace.path
        if path == "" or ask == True:
            path, selected = QFileDialog.getSaveFileName(self, "Salva workspace", "", "ShowSuite Cue (*.showcue)")
            if path == "":
                return
            if path.endswith(".showcue") == False:
                path = path + ".showcue"
        self.workspace.save(path)

    def _replace_workspace(self, workspace: Workspace) -> None:
        self.runtime.hard_stop_all()
        self.workspace = workspace
        self.services.stop()
        self.runtime = Runtime(workspace, self.runtime.clock, check_files=self.runtime.check_files)
        self.services = Services(self.runtime, **self.services_options)
        self.services.start()
        self.cart_view.runtime = self.runtime
        self.inspector.workspace = workspace
        self.inspector.load(None)
        self.refresh_tabs()
        self.refresh_tree()


def _real_midi_backend():
    try:
        from ..cue.outputs import MidoBackend
        return MidoBackend()
    except ImportError:
        return None


def _local_light_bridge(project_path: str):
    # Carica un progetto Light nello stesso processo e lo espone ai cue Light e alla dashboard.
    from ..cue.lightbridge import LocalLightBridge
    from ..light.control.actions import ActionRunner
    from ..light.engine import LightEngine
    from ..light.project import load
    engine = LightEngine(load(project_path))
    return LocalLightBridge(ActionRunner(engine))


def main() -> int:
    application = QApplication(sys.argv)
    options = {"osc_from_workspace": True, "use_audio_device": True, "live_network": True,
               "midi_backend": _real_midi_backend()}
    if "--light" in sys.argv:
        light_index = sys.argv.index("--light")
        if light_index + 1 < len(sys.argv):
            options["light_bridge"] = _local_light_bridge(sys.argv[light_index + 1])
    window = CueWindow(services_options=options)
    window.start_updates()
    for message in window.services.errors:
        window.status_label.setText(message)
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
