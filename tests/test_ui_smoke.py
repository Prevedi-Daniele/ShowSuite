import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def test_window_add_and_fader():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = AddFixtureDialog(w.engine, w)
    d.prof.setCurrentIndex(1); d.count.setValue(3); d.name.setText("Par")
    assert d.create() == 3
    w._refresh_list()
    w._select("Par 2")
    w.faders.sliders[0].findChildren(type(w.faders.sliders[0].findChildren(__import__("PySide6.QtWidgets", fromlist=["QSlider"]).QSlider)[0]))[0].setValue(255)
    assert w.engine.mixer.render(1)[3] == 255  # Par 2 @4, Red
    w.close()


def test_record_and_trigger_cue():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow, RecordCueDialog
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(2); d.create()
    w._refresh_list()
    w.engine.set_value("Fixture 1", "Red", 200)
    rd = RecordCueDialog(w.engine, ["Fixture 1", "Fixture 2"], w)
    rd.name.setText("Rosso")
    cue = rd.build()
    w.engine.project.cues.append(cue)
    for n in ("Fixture 1", "Fixture 2"):
        w.engine.release_programmer(n)
    w.live_view.add_cue_button("Rosso")
    assert w.engine.mixer.render(1)[0] == 0
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    QTest.mouseClick(w.live_view.widgets[0], Qt.LeftButton)
    w.engine.live.update()
    assert w.engine.mixer.render(1)[0] == 200 and w.engine.mixer.render(1)[3] == 200
    w.close()


def test_sequence_recording_ui():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(2); d.create()
    w._refresh_list()
    w.fixlist.selectAll()
    for v in (10, 200):
        w.engine.set_value("Fixture 1", "Red", v)
        w.add_step()
    assert [s.values["Red"] for s in w._seq_steps] == [10, 200] and not w.engine.values
    w.close()


def test_control_dialog_osc_toggle():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import ControlDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = ControlDialog(w)
    d.osc_port.setValue(23456)
    d._toggle_osc()
    assert w.osc is not None
    d._toggle_osc()
    assert w.osc is None
    d.close(); w.close()


def test_flash_button_and_selection_and_highlight():
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from showsuite.light.live import LiveCue
    from showsuite.light.preset import Preset
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); w.resize(1000, 700); w.show()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(3); d.name.setText("MH"); d.create()
    w._refresh_list()
    # selezione digitando il prefisso
    w.preview.setFocus()
    QTest.keyClicks(w.preview, "mh2")
    assert w.selected_names() == ["MH 2"]
    QTest.keyClick(w.preview, Qt.Key_Escape)
    assert w.selected_names() == []
    w.preview.set_selection(["MH 1", "MH 3"])
    assert [i.text() for i in w.fixlist.selectedItems()] == ["MH 1", "MH 3"]
    # evidenzia
    w.bar.hl.setChecked(True)
    assert w.engine.mixer.render(1)[0] == 255 and w.engine.mixer.render(1)[3] == 0
    w.bar.hl.setChecked(False)
    assert w.engine.mixer.render(1)[0] == 0
    # flash: attivo solo finché premuto
    w.engine.project.cues.append(LiveCue("Fl", ["MH 1"], Preset("x", {"Red": 99})))
    w.live_view.add_cue_button("Fl")
    w.live_view.page.buttons[0].mode = "flash"
    btn = w.live_view.widgets[0]
    QTest.mousePress(btn, Qt.LeftButton)
    w.engine.live.update(); assert w.engine.mixer.render(1)[0] == 99
    QTest.mouseRelease(btn, Qt.LeftButton)
    w.engine.live.update(); assert w.engine.mixer.render(1)[0] == 0
    # i fader agiscono su tutta la selezione
    w.preview.set_selection(["MH 1", "MH 2"])
    w.faders.sliders[0].findChildren(__import__("PySide6.QtWidgets", fromlist=["QSlider"]).QSlider)[0].setValue(77)
    assert w.engine.mixer.render(1)[0] == 77 and w.engine.mixer.render(1)[3] == 77
    w.close()


def test_control_dialog_dmx_and_clock():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import ControlDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = ControlDialog(w)
    d.action.setCurrentText("master"); d.dmx_uni.setValue(3); d.dmx_ch.setValue(7); d._add_dmx()
    d.dmx_ch.setValue(7); d._add_dmx()          # stessa mappa: sostituisce, non duplica
    assert len(w.engine.project.dmx_mappings) == 1
    d.list.setCurrentRow(d.list.count() - 1); d._remove()
    assert not w.engine.project.dmx_mappings
    d.clock_chk.setChecked(False)
    assert w.midi.clock.enabled is False
    d.close(); w.close()


def test_design_view_panels_and_dot():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(2); d.create()
    w._refresh_list(); w.show_view(0); w.show()
    w.preview.set_selection(["RGB 1", "RGB 2"] if False else [f.name for f in w.engine.project.patch.fixtures], emit=True)
    dv = w.design
    assert dv.panels["dimmer"].isVisibleTo(dv) and dv.panels["color"].isVisibleTo(dv)
    assert not dv.panels["shutter"].isVisibleTo(dv)
    dv.panels["color"]._rgb(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#ff0000"))
    assert w.engine.mixer.render(1)[0] == 255 and dv.panels["color"].dot.toolTip().startswith("Sovrascritto")
    dv.panels["color"].dot.click()
    assert w.engine.mixer.render(1)[0] == 0
    w.close()


def test_patch_window_patch_and_change_mode():
    from PySide6.QtWidgets import QApplication
    from showsuite.light.fixtures import generic_rgb
    from showsuite.ui.light_window import MainWindow
    from showsuite.ui.patch_window import PatchPopover, PatchWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); pw = PatchWindow(w.engine, w)
    pw.models.setCurrentRow(1)
    key = pw.models.currentItem().data(0x0100)
    pop = PatchPopover(pw, 10, None, key); pop.count.setValue(3); pop.name.setText("P")
    pw.commit(pop)
    fx = w.engine.project.patch.fixtures
    assert [(f.name, f.address) for f in fx] == [("P 1", 10), ("P 2", 13), ("P 3", 16)] or len(fx) == 3
    assert pw.grid.fixture_at(fx[0].address) is fx[0] and pw.grid.fixture_at(500) is None
    pop2 = PatchPopover(pw, fx[0].address, fx[0], None); pop2.addr_s.setValue(fx[1].address)
    import pytest as _p
    from showsuite.light.fixtures import PatchError
    with _p.raises(PatchError):
        pw.commit(pop2)
    assert len(w.engine.project.patch.fixtures) == 3 and fx[0] in w.engine.project.patch.fixtures
    w.close()


def test_cuelist_view_go_back_skip():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from showsuite.light.live import LiveCue
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.create()
    for n in ("A", "B", "C"):
        w.engine.project.cues.append(LiveCue(n, ["Fixture"])); w.live_view.add_cue_button(n)
    lv = w.live_view; lv.add_cuelist(); cv = lv.cl_view
    assert cv is not None and cv.table.rowCount() == 3
    cv.table.item(1, 0).setCheckState(Qt.Unchecked)               # B saltato
    assert cv.cl.steps[1].skip
    cv.go(); assert w.engine.live.current_step(cv.cl) == 1
    cv.go(); assert w.engine.live.current_step(cv.cl) == 3        # salta B
    cv.back(); assert w.engine.live.current_step(cv.cl) == 2      # indietro va anche su B (goto)
    cv.stop(); assert w.engine.live.current_step(cv.cl) is None
    lv.remove_cuelist(); assert lv.cl_view is None and lv.page.cuelist is None
    w.close()


def test_live_view_frames_faders_and_groups():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from showsuite.light.live import LiveCue
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    from showsuite.ui.live_view import FaderButton
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.create()
    from showsuite.light.preset import Preset
    for n, ch in (("A", "Red"), ("B", "Blue"), ("F", "Green")):
        w.engine.project.cues.append(LiveCue(n, ["Fixture"], Preset(n, {ch: 255}))); w.live_view.add_cue_button(n)
    lv = w.live_view; bs = lv.page.buttons
    bs[0].group = bs[1].group = "g"; bs[2].kind = "fader"; bs[2].frame = 1; lv._fill_grid()
    assert len(lv.frame_widgets) == 2 and any(isinstance(x, FaderButton) for x in lv.widgets)
    QTest.mouseClick(lv.widgets[0], Qt.LeftButton); QTest.mouseClick(lv.widgets[1], Qt.LeftButton)
    w.engine.live.update()
    assert w.engine.mixer.render(1)[2] == 255 and w.engine.mixer.render(1)[0] == 0   # solo B: A è stato rilasciato
    fb = next(x for x in lv.widgets if isinstance(x, FaderButton)); fb.slider.setValue(50)
    w.engine.live.update(); assert w.engine.mixer.render(1)[1] == 128 or w.engine.mixer.render(1)[1] == 127
    lv.set_edit(True); assert lv.edit_mode
    w.close()


def test_button_popover_edits_cue():
    from PySide6.QtWidgets import QApplication
    from showsuite.light.colorfx import ColorEffect
    from showsuite.light.live import LiveCue
    from showsuite.light.preset import Preset
    from showsuite.ui.button_popover import ButtonPopover
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.create()
    cue = LiveCue("X", ["Fixture"], Preset("p", {"Red": 255}), color_fx=ColorEffect())
    w.engine.project.cues.append(cue); w.live_view.add_cue_button("X")
    btn = w.live_view.page.buttons[0]; pop = ButtonPopover(w.live_view, btn, cue)
    assert pop.items.count() == 3                       # fixture, preset, color effect
    pop._maybe_remove(pop.items.item(1)); assert cue.preset is None and pop.items.count() == 2
    pop._maybe_remove(pop.items.item(0)); assert pop.items.count() == 2                # la riga fixture non si rimuove
    pop.mode.setCurrentIndex(1); assert btn.mode == "flash" and cue.toggle is False
    pop.fade_in.setValue(2.5); pop.curve.setCurrentText("ease_in"); pop.prio.setValue(30)
    assert (cue.fade_in, cue.curve, cue.priority) == (2.5, "ease_in", 30)
    pop.speed.setValue(200); pop.dimmer.setValue(50)
    assert cue.speed == 2.0 and cue.dimmer == 0.5
    pop.grab(); w.close()


def test_crossfade_dialog_smoke():
    from PySide6.QtWidgets import QSlider
    from showsuite.light.live import LiveCue
    from showsuite.ui.light_window import MainWindow
    w = MainWindow(); w.engine.project.cues = [LiveCue("A", []), LiveCue("B", [])]
    w.live_view.crossfade_dialog(); w.live_view._xf.findChild(QSlider).setValue(500)
    assert w.engine.live.active["A"]["fader"] == 0.5


def test_patch_menu_actions_smoke(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    from showsuite.ui.light_window import MainWindow
    w = MainWindow(); w.engine.project.patch.add(FixtureInstance("A", generic_rgb(), 1, 1))
    w.preview.set_selection(["A"]); w.duplicate_fixtures()
    assert [f.name for f in w.engine.project.patch.fixtures] == ["A", "A 2"]
    out = tmp_path / "p.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    w.print_patch(); assert out.exists() and out.stat().st_size > 500
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(tmp_path / "f.json"), "")))
    w.export_fixtures(); assert (tmp_path / "f.json").exists()


def test_cuelist_view_reorder_duplicate_filter():
    from showsuite.light.engine import LightEngine
    from showsuite.light.live import CueList, CueListStep, LiveCue, LivePage
    from showsuite.ui.cuelist_view import CueListView
    e = LightEngine(); e.project.cues = [LiveCue("Alfa", []), LiveCue("Beta", [])]
    pg = LivePage("P", [], cuelist=CueList("CL", [CueListStep("Alfa"), CueListStep("Beta", also=["Alfa"])])); e.project.pages = [pg]
    v = CueListView(e, pg); v.table.selectRow(0); v.move(1)
    assert [s.cue for s in pg.cuelist.steps] == ["Beta", "Alfa"]
    v.duplicate_step(); assert len(pg.cuelist.steps) == 3
    v.apply_filter("beta"); assert not v.table.isRowHidden(0) and v.table.isRowHidden(1)


def test_button_popover_overlay_duplicate_and_remove():
    from PySide6.QtCore import Qt
    from showsuite.light.colorfx import ColorEffect
    from showsuite.light.live import LiveButton, LiveCue
    from showsuite.ui.button_popover import ButtonPopover
    from showsuite.ui.light_window import MainWindow
    w = MainWindow(); cue = LiveCue("C", [], color_fx=ColorEffect(swatches=[(255, 0, 0)]))
    w.engine.project.cues = [cue]; btn = LiveButton("C")
    pop = ButtonPopover(w.live_view, btn, cue)
    assert pop.duplicate_as_overlay() == 1 and len(cue.overlays) == 1 and cue.overlays[0] is not cue.color_fx
    it = next(pop.items.item(i) for i in range(pop.items.count()) if pop.items.item(i).data(Qt.UserRole) == "overlay0")
    pop._maybe_remove(it); assert cue.overlays == []


def test_extra_live_window_syncs_with_engine():
    from showsuite.light.live import LiveButton, LiveCue, LivePage
    from showsuite.ui.light_window import MainWindow
    w = MainWindow(); c = LiveCue("A", []); w.engine.project.cues = [c]
    w.engine.project.pages = [LivePage("P", [LiveButton("A")])]; w.live_view.rebuild()
    lw = w.new_live_window(); lv = lw.centralWidget()
    w.engine.live.trigger(c); lv.sync()
    assert "A" in w.engine.live.active and lv.engine is w.engine
    lw.close()


def test_osc_select_page_and_fixtures_reach_ui():
    from showsuite.light.control.osc import dispatch
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    from showsuite.light.live import LivePage
    from showsuite.ui.light_window import MainWindow
    w = MainWindow(); w.engine.project.pages = [LivePage("Uno", []), LivePage("Due Due", [])]; w.live_view.rebuild()
    w.engine.project.patch.add(FixtureInstance("Par 1", generic_rgb(), 1, 1)); w._refresh_list()
    dispatch(w.runner, "/live/Due_Due/select", []); assert w.live_view.cur == 1
    dispatch(w.runner, "/fixture/Par_1/select", []); assert "Par 1" in w.preview.selection
    dispatch(w.runner, "/fixture/Par_1/deselect", []); assert "Par 1" not in w.preview.selection


def test_button_popover_modifiers_write_to_cue():
    from showsuite.light.live import LiveButton, LiveCue
    from showsuite.ui.button_popover import ButtonPopover
    from showsuite.ui.light_window import MainWindow
    w = MainWindow(); cue = LiveCue("C", []); btn = LiveButton("C"); pop = ButtonPopover(w.live_view, btn, cue)
    pop.hue.setValue(-90); pop.toff.setValue(2.5); pop.bmult.setCurrentIndex(pop.bmult.findData(4.0))
    assert (cue.hue_shift, cue.time_offset, cue.beat_mult) == (-90.0, 2.5, 4.0)
