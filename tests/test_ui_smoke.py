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
