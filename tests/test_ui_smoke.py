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
    w.livedock.rebuild()
    assert w.engine.mixer.render(1)[0] == 0
    w.livedock.buttons["Rosso"].click()
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
