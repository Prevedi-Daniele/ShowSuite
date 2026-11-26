import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import Workspace


def make_runtime():
    workspace = Workspace("S")
    workspace.settings["passcodes"] = [{"passcode": "", "view": True, "edit": True, "control": True}]
    cue = workspace.new_cue("wait", name="Uno")
    cue.number = "1"
    cue.triggers["hotkey"] = "A"
    cue.triggers["midi"] = {"kind": "note_on", "channel": 1, "byte1": 60}
    return workspace, Runtime(workspace, ManualClock()), cue


def test_log_disabilitato_di_default_e_abilitabile():
    workspace, runtime, cue = make_runtime()
    runtime.logs.add("osc_in", "/go")
    assert runtime.logs.lines() == []
    runtime.logs.set_enabled("osc_in", True)
    runtime.logs.add("osc_in", "/go")
    runtime.logs.add("trigger", "ignorato")
    assert len(runtime.logs.lines()) == 1
    assert runtime.logs.lines(["osc_in"], "GO")[0].endswith("[osc_in] /go")
    assert runtime.logs.lines(["osc_in"], "altro") == []
    with pytest.raises(ValueError):
        runtime.logs.set_enabled("boh", True)
    assert workspace.settings["log_enabled"]["osc_in"] == True
    runtime.logs.clear()
    assert runtime.logs.lines() == []


def test_log_da_trigger_midi_e_osc():
    from showsuite.cue.qlab_api import QLabApi
    from showsuite.cue.triggers import TriggerManager
    from tests.test_cue_osc import MemoryClient
    workspace, runtime, cue = make_runtime()
    for category in ("trigger", "midi_in", "osc_in", "osc_out"):
        runtime.logs.set_enabled(category, True)
    triggers = TriggerManager(runtime)
    triggers.key_event("A", True)
    triggers.midi_in(bytes([0x90, 60, 100]))
    api = QLabApi([runtime])
    client = MemoryClient()
    api.handle("/cue/1/name", [], client)
    text = "\n".join(runtime.logs.lines())
    assert "avviato da trigger hotkey A" in text
    assert "avviato da trigger MIDI" in text
    assert "90 3c 64" in text
    assert "[osc_in] /cue/1/name" in text
    assert "[osc_out] /reply/cue/1/name ok" in text


def test_righe_trigger():
    from showsuite.ui.cue_status import trigger_rows
    workspace, runtime, cue = make_runtime()
    rows = trigger_rows(workspace)
    assert [row["kind"] for row in rows] == ["Tasto", "MIDI"]
    assert rows[0]["detail"] == "A" and "byte1=60" in rows[1]["detail"]


def test_finestra_status():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_status import WorkspaceStatusWindow
    QApplication.instance() or QApplication([])
    workspace, runtime, cue = make_runtime()
    window = WorkspaceStatusWindow(runtime)
    window.logs.boxes["osc_in"].setChecked(True)
    assert runtime.logs.enabled("osc_in") == True
    runtime.logs.add("osc_in", "/ciao")
    window.logs.refresh()
    assert "/ciao" in window.logs.text.toPlainText()
    window.logs.filter.setText("zzz")
    assert window.logs.text.toPlainText() == ""
    window.logs.filter.setText("")
    window.logs.clear()
    assert window.logs.text.toPlainText() == ""
    assert window.triggers.table.rowCount() == 2
    chosen = []
    window.triggers.cue_chosen.connect(chosen.append)
    window.triggers.table.cellClicked.emit(0, 0)
    assert chosen == [cue.unique_id]
