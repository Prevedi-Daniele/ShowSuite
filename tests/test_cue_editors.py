import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.model import TYPE_AUDIO, Workspace


def make_cue():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    workspace = Workspace("E")
    cue = workspace.new_cue(TYPE_AUDIO)
    cue.params["media_channels"] = 2
    return workspace, cue


def test_matrice_default_e_modifica_materializza_la_diagonale():
    from showsuite.ui.cue_editors import LevelsEditor
    workspace, cue = make_cue()
    editor = LevelsEditor(workspace)
    editor.load(cue)
    assert editor.crosspoint(0, 0) == 0.0 and editor.crosspoint(0, 1) <= -100
    editor.table.item(0, 1).setText("-6")
    assert cue.params["levels"]["1/2"] == -6.0
    assert cue.params["levels"]["1/1"] == 0.0 and cue.params["levels"]["2/2"] == 0.0
    editor.table.item(1, 1).setText("-inf")
    assert cue.params["levels"]["2/2"] <= -100
    editor.reset_matrix()
    assert [key for key in cue.params["levels"] if "/" in key] == []


def test_matrice_valore_non_valido_ripristina_la_cella():
    from showsuite.ui.cue_editors import LevelsEditor
    workspace, cue = make_cue()
    editor = LevelsEditor(workspace)
    editor.load(cue)
    editor.table.item(0, 0).setText("abc")
    assert editor.table.item(0, 0).text() == "0"
    assert "levels" not in cue.params or "1/1" not in cue.params["levels"]


def test_main_trim_e_numero_di_uscite_dalla_patch():
    from showsuite.ui.cue_editors import LevelsEditor
    workspace, cue = make_cue()
    workspace.patches["audio"] = [{"name": "A", "first_channel": 1, "channels": 4}]
    editor = LevelsEditor(workspace)
    editor.load(cue)
    assert editor.table.columnCount() == 4
    editor.main.setValue(-3.0)
    editor.trim.setValue(2.0)
    assert cue.params["levels"]["main"] == -3.0 and cue.params["trim"] == 2.0


def test_slice_editor_aggiunge_ordina_e_infinito():
    from showsuite.ui.cue_editors import SliceEditor
    workspace, cue = make_cue()
    cue.params["media_duration"] = 10.0
    editor = SliceEditor()
    editor.load(cue)
    editor.add_slice()
    editor.table.item(0, 0).setText("7")
    editor.add_slice()
    editor.table.item(1, 0).setText("3")
    editor.table.item(1, 1).setText("0")
    assert cue.params["slices"] == [{"time": 3.0, "play_count": "inf"}, {"time": 7.0, "play_count": 1}]
    editor.table.setCurrentCell(0, 0)
    editor.remove_selected()
    assert len(cue.params["slices"]) == 1
    editor.rate.setValue(2.0)
    editor.loop.setChecked(True)
    assert cue.params["rate"] == 2.0 and cue.params["infinite_loop"] == True


def test_envelope_editor_punti_ordinati_e_abilitazione():
    from showsuite.ui.cue_editors import EnvelopeEditor
    workspace, cue = make_cue()
    editor = EnvelopeEditor()
    editor.load(cue)
    editor.add_point()
    editor.add_point()
    editor.table.item(0, 0).setText("5")
    editor.table.item(0, 1).setText("-12")
    editor.enabled.setChecked(True)
    fade = cue.params["integrated_fade"]
    assert fade["enabled"] == True
    assert fade["points"] == [[2.0, 0.0], [5.0, -12.0]] or fade["points"] == [[1.0, 0.0], [5.0, -12.0]]
    editor.table.setCurrentCell(0, 0)
    editor.remove_selected()
    assert len(cue.params["integrated_fade"]["points"]) == 1


def test_inspector_mostra_le_schede_solo_per_cue_audio():
    from showsuite.ui.cue_window import Inspector
    workspace, cue = make_cue()
    inspector = Inspector(workspace)
    inspector.load(cue)
    titles = [inspector.tabs.tabText(index) for index in range(inspector.tabs.count())]
    assert titles[-3:] == ["Livelli", "Slice", "Envelope"]
    other = workspace.new_cue("wait")
    inspector.load(other)
    assert inspector.tabs.count() == 3
