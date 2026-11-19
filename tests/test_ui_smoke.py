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
