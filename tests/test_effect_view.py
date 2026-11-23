import os

import pytest

from showsuite.light import effectlib


def test_library():
    assert "Fire" in effectlib.search("fi") and effectlib.search("zzz") == []
    a, b = effectlib.get("Fire"), effectlib.get("Fire")
    a.swatches.append((1, 2, 3)); assert len(b.swatches) == len(effectlib.COLOR_LIBRARY["Fire"].swatches)
    for n in effectlib.COLOR_LIBRARY:
        c = effectlib.get(n).color(1.3, 1, 4); assert len(c) == 3 and all(0 <= v <= 255 for v in c)


def test_effect_view_try_and_make(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    w = MainWindow(); d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(3); d.create()
    w._refresh_list(); w.show_view(2); ev = w.effect_view
    ev.try_btn.setChecked(True); assert not ev.try_btn.isChecked()          # niente selezione
    w.preview.set_selection(["Fixture 1", "Fixture 2"])
    ev.search.setText("police"); ev._load(ev.lib.item(0))
    assert ev.color_ed.effect.crossfade is False and ev.color_ed.effect.swatches[0] == (255, 0, 0)
    ev.try_btn.setChecked(True); ev._tick()
    assert w.engine.mixer.render(1)[0] in (0, 255) and w.engine.values            # il programmer riceve il colore
    ev.try_btn.setChecked(False); assert not w.engine.values
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Sirena", True)))
    ev.make_button()
    cue = w.engine.project.cues[-1]
    assert cue.name == "Sirena" and cue.color_fx and cue.fixtures == ["Fixture 1", "Fixture 2"] and w.live_view.page.buttons[-1].cue == "Sirena"
    ev.make_button(); assert len(w.engine.project.cues) == 1                 # nome duplicato rifiutato
    ev.set_mode("position"); ev.make_button()
    assert w.engine.project.cues[-1].position_fx is None or w.engine.project.cues[-1].name == "Sirena"   # nome già usato: rifiutato
    w.show_view(0); assert not ev.try_btn.isChecked()
    w.close()



def test_pattern_editor_and_view(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    w = MainWindow(); d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(4); d.create(); w._refresh_list()
    for i, f in enumerate(w.engine.project.patch.fixtures):
        f.x = i / 3
    ev = w.effect_view; ev.set_mode("pattern"); ed = ev.pat_ed; got = []
    ed.changed.connect(got.append)
    ed.set_pattern("scanner"); assert ed.effect.pattern == "scanner" and set(ed.effect.params) <= {"length", "overshoot", "phase", "fringe", "noise"}
    ed.add_sample((0, 255, 0)); ed.edit_sample(0, QColor("#101010")); assert ed.effect.samples[0] == (16, 16, 16) and len(ed.effect.samples) == 3
    ed.duplicate_sample(1); ed.delete_sample(0); assert len(ed.effect.samples) == 3
    ed._param("length", 2); ed.order.setCurrentIndex(1); ed.group.setValue(2); ed.beat.setChecked(True); ed.mult.setCurrentIndex(3)
    e = ed.effect; assert (e.params["length"], e.order, e.grouping, e.beat_controlled, e.beat_mult) == (2, "right_left", 2, True, 2.0)
    ed.set_pattern("fire"); assert "length" not in ed.effect.params and ed.form.rowCount() == 3
    w.preview.set_selection([f.name for f in w.engine.project.patch.fixtures])
    ev.try_btn.setChecked(True); ev._tick(); assert w.engine.values
    ev.try_btn.setChecked(False)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Fuoco", True)))
    ev.make_button(); c = w.engine.project.cues[-1]; assert c.name == "Fuoco" and c.pattern_fx.pattern == "fire" and c.color_fx is None
    ed.grab(); w.close()
