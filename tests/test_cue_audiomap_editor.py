import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF

from showsuite.cue import audiomap
from showsuite.cue.model import Workspace


def make_editor(workspace=None):
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_audiomap_editor import AudioMapEditor
    QApplication.instance() or QApplication([])
    return AudioMapEditor(workspace or Workspace("M"))


class FakeEvent:
    def __init__(self, point):
        self._point = point

    def position(self):
        return self._point


def test_nuova_mappa_rinomina_ed_elimina():
    workspace = Workspace("M")
    editor = make_editor(workspace)
    assert editor.current_map() is None
    editor.add_map()
    assert len(workspace.patches["audio_map"]) == 1
    editor.map_name.setText("Sala")
    editor._rename_map()
    assert workspace.patches["audio_map"][0]["name"] == "Sala"
    assert editor.map_box.itemText(0) == "Sala"
    editor.delete_map()
    assert workspace.patches["audio_map"] == []
    assert workspace.modified == True


def test_aggiunta_elementi_e_proprieta():
    workspace = Workspace("M")
    editor = make_editor(workspace)
    editor.add_map()
    for kind in ("marks", "filters", "objects"):
        editor.add_item(kind)
    audio_map = workspace.patches["audio_map"][0]
    assert len(audio_map["marks"]) == len(audio_map["filters"]) == len(audio_map["objects"]) == 1
    assert audio_map["objects"][0]["name"] == "A"
    editor.canvas.selected = ("marks", audio_map["marks"][0]["unique_id"])
    editor._selection_changed()
    editor.gravity_spin.setValue(9.0)
    assert audio_map["marks"][0]["gravity"] == 5.0
    editor.shadow_spin.setValue(30.0)
    assert audio_map["marks"][0]["shadow"] == 30.0


def test_trascinamento_sposta_oggetto_e_home():
    workspace = Workspace("M")
    editor = make_editor(workspace)
    editor.add_map()
    editor.add_item("objects")
    editor.resize(900, 560)
    editor.show()
    canvas = editor.canvas
    item = workspace.patches["audio_map"][0]["objects"][0]
    start = canvas.to_screen(item["x"], item["y"])
    canvas.mousePressEvent(FakeEvent(start))
    assert canvas.dragging == True
    target = QPointF(start.x() + 50, start.y() + 20)
    canvas.mouseMoveEvent(FakeEvent(target))
    canvas.mouseReleaseEvent(FakeEvent(target))
    assert item["x"] > 500.0 and item["y"] > 500.0
    assert item["home_x"] == item["x"]
    assert editor.x_spin.value() == pytest.approx(item["x"], abs=0.01)


def test_clic_nel_vuoto_deseleziona():
    editor = make_editor()
    editor.add_map()
    editor.add_item("marks")
    editor.canvas.mousePressEvent(FakeEvent(QPointF(2, 2)))
    assert editor.canvas.selected is None
    assert editor.delete_item_button.isEnabled() == False


def test_livelli_mark_e_anteprima_oggetto():
    workspace = Workspace("M")
    editor = make_editor(workspace)
    editor.add_map()
    audio_map = workspace.patches["audio_map"][0]
    mark = audiomap.add_mark(audio_map, "Sinistra", 100, 500, {1: 0.0, 2: -200.0})
    audiomap.add_object(audio_map, None, 100, 500)
    editor.canvas.selected = ("marks", mark["unique_id"])
    editor._selection_changed()
    assert editor.levels_table.rowCount() == 2
    editor.levels_table.item(1, 1).setText("-6")
    assert mark["levels"][2] == -6.0
    editor.levels_table.item(0, 0).setText("abc")
    assert mark["levels"] == {1: 0.0, 2: -6.0}
    assert editor.levels_table.item(0, 0).text() == "1"
    editor.add_level()
    assert 0 in mark["levels"]
    editor.canvas.selected = ("objects", audio_map["objects"][0]["unique_id"])
    editor._selection_changed()
    assert "u1" in editor.preview.text()


def test_elimina_elemento():
    workspace = Workspace("M")
    editor = make_editor(workspace)
    editor.add_map()
    editor.add_item("filters")
    editor.delete_item()
    assert workspace.patches["audio_map"][0]["filters"] == []
