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

