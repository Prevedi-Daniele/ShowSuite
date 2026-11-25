import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_AUDIO, TYPE_WAIT, Workspace


def make():
    workspace = Workspace("A")
    first = workspace.new_cue(TYPE_WAIT, name="Attesa")
    first.duration = 10.0
    second = workspace.new_cue(TYPE_AUDIO, name="Brano")
    second.params["file_target"] = "/non/esiste.wav"
    runtime = Runtime(workspace, ManualClock(), check_files=True)
    return workspace, runtime, first, second


def test_righe_active_cues():
    from showsuite.ui.cue_active import active_rows
    workspace, runtime, first, second = make()
    assert active_rows(runtime) == []
    runtime.start_cue(first)
    runtime.advance(2.0)
    rows = active_rows(runtime)
    assert len(rows) == 1 and rows[0]["phase"] == "In corso" and rows[0]["elapsed"] == pytest.approx(2.0)
    runtime.pause_cue(first)
    assert active_rows(runtime)[0]["phase"] == "In pausa"


def test_righe_avvisi_per_cue_broken():
    from showsuite.ui.cue_active import warning_rows
    workspace, runtime, first, second = make()
    rows = warning_rows(runtime)
    assert [row["cue"] for row in rows] == [second]
    assert rows[0]["reason"] != ""


def test_finestra_active_cues_comandi():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_active import ActiveCuesWindow, WarningsWindow
    QApplication.instance() or QApplication([])
    workspace, runtime, first, second = make()
    runtime.start_cue(first)
    window = ActiveCuesWindow(runtime)
    window.refresh()
    assert window.table.rowCount() == 1
    window.table.selectRow(0)
    window.pause_selected()
    assert runtime.status(first)["paused"] == True
    window.resume_selected()
    window.stop_selected()
    assert runtime.is_running(first) == False
    assert WarningsWindow(runtime).table.rowCount() == 1
