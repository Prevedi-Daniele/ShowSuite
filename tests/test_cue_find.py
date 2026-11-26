import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.model import Workspace
from showsuite.ui.cue_find import FindWindow, find_cues


def make_workspace():
    workspace = Workspace("F")
    first = workspace.new_cue("wait")
    first.number = "10"
    first.name = "Apertura"
    second = workspace.new_cue("audio")
    second.number = "20"
    second.name = "Musica"
    second.notes = "da rivedere con apertura"
    return workspace, first, second


def test_cerca_per_campo_e_maiuscole():
    workspace, first, second = make_workspace()
    assert find_cues(workspace, "apertura") == [first, second]
    assert find_cues(workspace, "apertura", ("name",)) == [first]
    assert find_cues(workspace, "apertura", ("name",), True) == []
    assert find_cues(workspace, "Apertura", ("name",), True) == [first]
    assert find_cues(workspace, "20", ("number",)) == [second]
    assert find_cues(workspace, "audio", ("type",)) == [second]
    assert find_cues(workspace, "") == []


def test_finestra_emette_selezione():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    workspace, first, second = make_workspace()
    window = FindWindow(workspace)
    chosen = []
    window.cue_chosen.connect(chosen.append)
    window.query.setText("musica")
    assert window.results.count() == 1
    assert window.count_label.text() == "1 trovati"
    window.results.itemClicked.emit(window.results.item(0))
    assert chosen == [second.unique_id]


def test_cue_window_seleziona_trovato():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_window import CueWindow
    QApplication.instance() or QApplication([])
    workspace, first, second = make_workspace()
    window = CueWindow(workspace)
    window.open_find()
    window.tool_windows["find"].query.setText("musica")
    window.select_cue_by_id(second.unique_id)
    assert window.selected_cues() == [second]
