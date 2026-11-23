import os

import pytest


def make(monkeypatch=None):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from showsuite.light.live import LiveCue
    from showsuite.light.preset import Palette, Preset
    from showsuite.light.stage import make_group
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(4); d.create()
    w._refresh_list(); pr = w.engine.project
    make_group(pr.groups, "Arco", ["Fixture 1", "Fixture 2"])
    pr.palettes = [Palette("Colors", [Preset("Rosso", {"Red": 255}), Preset("Blu", {"Blue": 255})], "Arco"),
                   Palette("Posizioni", [Preset("Su", {"Tilt": 10})])]
    pr.cues.append(LiveCue("Chase", ["Fixture 3"]))
    w.palette_tree.refresh()
    return w


def top_names(t):
    return [t.topLevelItem(i).text(0) for i in range(t.topLevelItemCount())]


def test_tree_structure_filter_and_apply():
    w = make(); t = w.palette_tree
    assert top_names(t) == ["Arco", "Tutti i fixture", "Effetti"]
    arco = t.topLevelItem(0); pal = arco.child(0); assert pal.text(0) == "Colors" and pal.childCount() == 2
    assert pal.child(0).icon(0).isNull() is False
    t.activate(pal.child(0))                                   # palette del gruppo "Arco": applica ai suoi fixture
    d = w.engine.mixer.render(1)
    assert d[0] == 255 and w.engine.values.keys() == {"Fixture 1", "Fixture 2"}
    t.set_filter("blu"); assert t.topLevelItem(0).child(0).childCount() == 1
    t.set_filter(""); t.activate(t.topLevelItem(2).child(0))   # effetto: parte il cue
    assert "Chase" in w.engine.live.active
    w.close()


def test_move_palette_between_folders_and_add_preset(monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    w = make(); t = w.palette_tree; pr = w.engine.project
    pr.palettes[1].group = "Arco"; t.refresh()
    assert t.topLevelItem(0).childCount() == 2
    pr.palettes[1].group = ""; t.refresh()
    w.preview.set_selection(["Fixture 4"]); w.engine.set_value("Fixture 4", "Green", 200)
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("Colors", True)))
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Verde", True)))
    t.add_from_programmer()
    assert [p.name for p in pr.palettes[0].presets] == ["Rosso", "Blu", "Verde"] and pr.palettes[0].presets[-1].values == {"Green": 200}
    w.close()


def test_palette_group_saved(tmp_path):
    from showsuite.light import project as pj
    w = make(); f = tmp_path / "p.showsuite-light"; pj.save(w.engine.project, str(f))
    assert pj.load(str(f)).palettes[0].group == "Arco"
    w.close()
