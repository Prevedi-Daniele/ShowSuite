import os

import pytest

from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance
from showsuite.light.fixtures.ofl import parse_ofl
from showsuite.light.posfx import PATTERNS, PositionEffect


def test_all_patterns_bounded_and_periodic():
    for name in PATTERNS:
        fx = PositionEffect(name, 4.0)
        for i in range(50):
            x, y = fx.point(i * 0.2, 1, 4)
            assert -1 <= x <= 1 and -1 <= y <= 1
        if name != "Random Dots":
            a, b = fx.point(0.3), fx.point(4.3)
            assert a == pytest.approx(b, abs=1e-9)


def test_offsets_and_apply():
    pan = PositionEffect("Pan Track", 4.0, time_offset=0.0)
    r = pan.evaluate(["A", "B"], 1.0)
    assert r["A"] == r["B"] and r["A"][0] == pytest.approx(0.9)     # picco del seno a 1/4 di ciclo
    shifted = PositionEffect("Pan Track", 4.0, time_offset=0.5).evaluate(["A", "B"], 0.0)
    assert shifted["A"][0] == 0 and shifted["B"][0] > 0.3
    (prof,) = parse_ofl({"name": "M", "availableChannels": {"Pan": {"capability": {"type": "Pan"}},
                         "Tilt": {"capability": {"type": "Tilt"}}}, "modes": [{"name": "m", "channels": ["Pan", "Tilt"]}]}, "X")
    e = LightEngine(); e.project.patch.add(FixtureInstance("M1", prof, 1, 1))
    PositionEffect("Tilt Track 2", 4.0).apply(e, ["M1"], 1.0)
    d = e.mixer.render(1); assert d[0] == 128 and d[1] > 240
    with pytest.raises(ValueError):
        PositionEffect("boh").point(0)


def test_editor_smoke():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.effect_editor import PositionEffectEditor
    app = QApplication.instance() or QApplication([])
    ed = PositionEffectEditor(); got = []
    ed.changed.connect(got.append)
    ed.icons["Bow Tie"].click(); ed.toff.setValue(40)
    assert ed.effect.pattern == "Bow Tie" and ed.effect.time_offset == 0.4 and len(got) >= 2
    ed.resize(900, 300); ed.grab()


def test_movement_path_and_reverse_and_templates():
    import pytest
    from showsuite.light.posfx import POSITION_LIBRARY, PositionEffect, position_template
    e = PositionEffect("Path", 4.0, 0.0, path=[(-1, 0), (0, 1), (1, 0), (0, -1)], smooth=False)
    assert e.point(0, 0, 1) == pytest.approx((-1, 0)) and e.point(1.0, 0, 1) == pytest.approx((0, 1))
    assert PositionEffect("Path", 4.0, 0.0, path=e.path, smooth=False, reverse=True).point(1.0, 0, 1) == pytest.approx((0, -1))
    s = PositionEffect("Path", 4.0, 0.0, path=e.path, smooth=True)
    for t in (0.3, 1.7, 3.9):
        x, y = s.point(t, 0, 1); assert -1 <= x <= 1 and -1 <= y <= 1
    assert PositionEffect("Path", 1.0, path=[]).point(0.5) == (0.0, 0.0)
    t = position_template("Slow Circle"); t.size = 0.1; assert POSITION_LIBRARY["Slow Circle"].size == 0.5
    from showsuite.light import project as pj
    from showsuite.light.live import LiveCue
    p = pj.Project("P"); p.cues = [LiveCue("m", [], position_fx=e)]
    q = pj.loads(pj.dumps(p)); assert [tuple(x) for x in q.cues[0].position_fx.path] == [(-1, 0), (0, 1), (1, 0), (0, -1)]
