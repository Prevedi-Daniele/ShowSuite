import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.model import Workspace


def make_dialog(workspace):
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_patch_dialog import PatchDialog
    QApplication.instance() or QApplication([])
    return PatchDialog(workspace)


def test_aggiungi_modifica_e_applica_patch():
    workspace = Workspace("P")
    dialog = make_dialog(workspace)
    dialog.add_patch("network")
    dialog.tables["network"].item(0, 2).setText("192.168.1.20")
    dialog.tables["network"].item(0, 3).setText("8000")
    dialog.add_patch("audio")
    dialog.tables["audio"].item(0, 2).setText("3")
    dialog.apply()
    assert workspace.patches["network"][0]["host"] == "192.168.1.20"
    assert workspace.patches["network"][0]["port"] == 8000
    assert workspace.patches["audio"][0]["first_channel"] == 3
    assert workspace.modified == True


def test_carica_patch_esistenti_e_rimuove():
    workspace = Workspace("P")
    workspace.patches["midi"] = [{"name": "Uno", "device": "A"}, {"name": "Due", "device": "B"}]
    dialog = make_dialog(workspace)
    assert dialog.tables["midi"].rowCount() == 2
    dialog.tables["midi"].setCurrentCell(0, 0)
    dialog.remove_patch("midi")
    dialog.apply()
    assert [entry["name"] for entry in workspace.patches["midi"]] == ["Due"]


def test_valore_non_valido_e_regioni_json():
    workspace = Workspace("P")
    dialog = make_dialog(workspace)
    dialog.add_patch("video_stage")
    dialog.tables["video_stage"].item(0, 3).setText('[{"name": "L", "bounds": [0, 0, 10, 10]}]')
    dialog.add_patch("network")
    dialog.tables["network"].item(0, 3).setText("abc")
    with pytest.raises(ValueError):
        dialog.collect()
    dialog.tables["network"].item(0, 3).setText("9000")
    collected = dialog.collect()
    assert collected["video_stage"][0]["regions"][0]["name"] == "L"
