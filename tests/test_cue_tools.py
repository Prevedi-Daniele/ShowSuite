import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from showsuite.cue.model import Workspace
from showsuite.cue.properties import copy_properties, paste_properties


def make_cues():
    workspace = Workspace("T")
    source = workspace.new_cue("wait")
    source.pre_wait = 2.0
    source.post_wait = 3.0
    source.color = "red"
    source.notes = "nota"
    source.number = "1"
    other = workspace.new_cue("wait")
    other.number = "2"
    audio = workspace.new_cue("audio")
    return workspace, source, other, audio


def test_copia_incolla_gruppi_e_tipi():
    workspace, source, other, audio = make_cues()
    snapshot = copy_properties(source)
    changed = paste_properties(snapshot, [other, audio], ["timing"])
    assert changed == 2
    assert other.pre_wait == 2.0 and audio.post_wait == 3.0
    assert other.color == "none" and other.number == "2"
    paste_properties(snapshot, [other], ["appearance"])
    assert other.color == "red" and other.notes == "nota"
    source.params["duration"] = 9
    snapshot = copy_properties(source)
    other.params = {}
    audio_params = dict(audio.params)
    paste_properties(snapshot, [other, audio], ["params"])
    assert other.params["duration"] == 9
    assert audio.params == audio_params
    snapshot["params"]["duration"] = 1
    assert other.params["duration"] == 9
    with pytest.raises(ValueError):
        paste_properties(snapshot, [other], ["boh"])
    assert paste_properties(snapshot, [other], []) == 0


def test_override_controls_scrive_impostazioni():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_tools import OverrideControlsWindow
    QApplication.instance() or QApplication([])
    workspace = Workspace("O")
    window = OverrideControlsWindow(workspace)
    assert window.active_overrides() == []
    window.boxes["midiOutput"].setChecked(True)
    assert workspace.settings["overrides"]["midiOutput"] == False
    assert "midiOutput" in window.status.text()
    window.boxes["midiOutput"].setChecked(False)
    assert workspace.settings["overrides"]["midiOutput"] == True
    assert window.status.text() == "Nessun override attivo"
    assert "dmxInput" not in window.boxes and "dmxOutput" in window.boxes


def test_timecode_status_righe():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from showsuite.cue.engine import ManualClock, Runtime
    from showsuite.cue.triggers import TriggerManager
    from showsuite.ui.cue_tools import TimecodeStatusWindow
    QApplication.instance() or QApplication([])
    workspace = Workspace("TC")
    group = workspace.new_cue("group")
    group.name = "Musical"
    group.params["timecode_sync"] = True
    clock = ManualClock()
    runtime = Runtime(workspace, clock)
    triggers = TriggerManager(runtime)
    window = TimecodeStatusWindow(runtime, triggers)
    assert window.rows() == [["Musical", "1", "--:--:--:--", "nessun segnale", ""]]
    triggers.timecode_input(group, 61.0)
    clock.advance(2.0)
    row = window.rows()[0]
    assert row[2] == "00:01:01:00" and row[3] == "in corso" and row[4] == "2.0 s fa"
    window.refresh()
    assert window.table.item(0, 2).text() == "00:01:01:00"


def test_finestra_incolla_proprieta_e_menu():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_tools import PastePropertiesDialog
    from showsuite.ui.cue_window import CueWindow
    QApplication.instance() or QApplication([])
    workspace, source, other, audio = make_cues()
    dialog = PastePropertiesDialog()
    assert dialog.chosen_groups() == ["timing", "appearance"]
    window = CueWindow(workspace)
    window.select_cue_by_id(source.unique_id)
    window.copy_properties()
    assert window.property_clipboard["pre_wait"] == 2.0
    window._show_simple_tool("override")
    window._show_simple_tool("timecode")
    assert set(("override", "timecode")) <= set(window.tool_windows)
