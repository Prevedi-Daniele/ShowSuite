import os

import pytest

from showsuite.light.colorfx import ColorEffect, curve_value, hue_wheel
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_rgb


def test_curve_value_cyclic():
    pts = [(0.0, 0.0), (0.5, 1.0)]
    assert curve_value(pts, 0.0) == 0 and curve_value(pts, 0.5) == 1 and curve_value(pts, 1.0) == pytest.approx(0)
    assert curve_value(pts, 0.25) == pytest.approx(0.5) and curve_value(pts, 1.25) == pytest.approx(0.5)
    assert curve_value([(0.3, 0.7)], 0.9) == 0.7


def test_swatch_crossfade_and_offset():
    fx = ColorEffect(swatches=[(255, 0, 0), (0, 0, 255)], duration=4.0, time_offset=0.0)
    assert fx.color(0) == (255, 0, 0) and fx.color(1.0) == (128, 0, 128) or fx.color(1.0)[0] > 100
    assert fx.color(2.0) == (0, 0, 255)
    hard = ColorEffect(swatches=[(255, 0, 0), (0, 0, 255)], duration=4.0, time_offset=0.0, crossfade=False)
    assert hard.color(1.0) == (255, 0, 0)
    spread = ColorEffect(swatches=[(255, 0, 0), (0, 0, 255)], duration=4.0, time_offset=1.0)
    c = spread.evaluate(["a", "b"], 0.0); assert c["a"] == (255, 0, 0) and c["b"] == (0, 0, 255)


def test_hue_curve_rainbow_and_apply():
    fx = ColorEffect(mode="curves", hue=hue_wheel(), saturation=[(0, 1.0)], brightness=[(0, 1.0)], duration=3.0, time_offset=0.0)
    r, g, b = fx.color(0.0)
    assert (r, g, b) == (255, 0, 0)
    assert fx.color(1.0)[1] > 150 and fx.color(2.0)[2] > 150      # verde, poi blu
    e = LightEngine(); e.project.patch.add(FixtureInstance("P", generic_rgb(), 1, 1))
    fx.apply(e, ["P"], 0.0); assert list(e.mixer.render(1)[:3]) == [255, 0, 0]


def test_editor_smoke():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.color_effect_editor import ColorEffectEditor
    app = QApplication.instance() or QApplication([])
    ed = ColorEffectEditor(); got = []
    ed.changed.connect(got.append)
    ed.add_swatch((0, 255, 0)); ed.edit_swatch(0, QColor("#ffff00"))
    assert ed.effect.swatches[0] == (255, 255, 0) and len(ed.effect.swatches) == 3
    ed.mode_btn.setChecked(False); assert ed.effect.mode == "curves"
    ed.curve.pts.append((0.7, 0.2)); ed.curve.changed.emit()
    ed.resize(800, 320); ed.grab()
