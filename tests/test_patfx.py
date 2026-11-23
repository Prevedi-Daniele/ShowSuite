import pytest
from types import SimpleNamespace as N

from showsuite.light.patfx import DEFAULTS, ORDERS, PATTERNS, PatternEffect


def row(n=8, y=0.5):
    return [N(name=f"F{i + 1}", x=i / max(1, n - 1), y=y, universe=1, address=1 + i * 3) for i in range(n)]


def reds(eff, fx, t=0.0, beats=0.0):
    r = eff.evaluate(fx, t, beats)
    return [r[f.name][0] for f in fx]


@pytest.mark.parametrize("pat", PATTERNS)
@pytest.mark.parametrize("t", [0.0, 0.37, 2.9, 17.2])
def test_every_pattern_valid_and_deterministic(pat, t):
    fx = row(10)
    e = PatternEffect(pat, [(10, 10, 10), (255, 0, 0), (0, 255, 0), (0, 0, 255)], duration=2.0)
    a, b = e.evaluate(fx, t), e.evaluate(fx, t)
    assert a == b and len(a) == 10
    assert all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in a.values())
    assert set(e.params) <= set(DEFAULTS[pat])


def test_chase_steps_smooth_offset_delay():
    fx = row(4)
    e = PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], duration=1.0)
    assert e.evaluate(fx, 0.0)["F1"] == (255, 0, 0) and e.evaluate(fx, 1.0)["F1"] == (0, 0, 255)
    assert e.evaluate(fx, 2.0)["F1"] == (255, 0, 0)                      # ciclico
    off = PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], params={"time_offset": 1.0})
    r = off.evaluate(fx, 0.0); assert r["F1"] == (255, 0, 0) and r["F2"] == (0, 0, 255)   # ogni pixel un passo indietro
    spv = PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], params={"steps_per_value": 2})
    assert spv.evaluate(fx, 1.0)["F1"] == (255, 0, 0) and spv.evaluate(fx, 2.0)["F1"] == (0, 0, 255)
    sm = PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], params={"smoothness": 1.0})
    mid = sm.evaluate(fx, 0.5)["F1"]; assert 100 < mid[0] < 155 and 100 < mid[2] < 155
    dl = PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], params={"delay": 1.0})
    assert dl.evaluate(fx, 0.5)["F3"] == (255, 0, 0)                      # non è ancora partito


def test_scanner_moves_back_and_forth():
    fx = row(8)
    e = PatternEffect("scanner", [(0, 0, 0), (255, 0, 0)], params={"length": 2}, duration=1.0)
    assert reds(e, fx, 0.0) == [255, 255, 0, 0, 0, 0, 0, 0]
    mid = reds(e, fx, 1.0)                                                # a metà percorso (c/2=0.5 -> estremo destro)
    assert mid[-1] == 255 and mid[0] == 0
    assert reds(e, fx, 2.0) == reds(e, fx, 0.0)


def test_fill_yoyo_rain():
    fx = row(4)
    f = PatternEffect("fill", [(0, 0, 0), (255, 0, 0)], duration=1.0)
    assert reds(f, fx, 0.0) == [0, 0, 0, 0] and reds(f, fx, 0.5) == [255, 255, 255, 255]
    y = PatternEffect("yoyo", [(0, 0, 0), (255, 0, 0)], duration=1.0)
    assert reds(y, fx, 0.5) == [255, 255, 255, 255] and reds(y, fx, 0.0) == [0, 0, 0, 0]
    r = PatternEffect("rain", [(0, 0, 0), (255, 0, 0)], params={"length": 1, "distance": 3}, duration=1.0)
    for t in (0.0, 0.25, 0.5, 0.75):
        assert reds(r, row(4), t).count(255) == 1                          # una goccia ogni 4 pixel


def test_beat_controlled_and_multiplier():
    fx = row(4)
    e = PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], beat_controlled=True)
    assert e.evaluate(fx, 99.0, 0.0)["F1"] == (255, 0, 0) and e.evaluate(fx, 99.0, 1.0)["F1"] == (0, 0, 255)
    e.beat_mult = 2.0; assert e.evaluate(fx, 0.0, 0.5)["F1"] == (0, 0, 255)


def test_orders_grouping_repeat_origin():
    fx = [N(name=n, x=x, y=y, universe=1, address=a) for n, x, y, a in
          (("C", 0.9, 0.1, 5), ("A", 0.1, 0.9, 20), ("B", 0.5, 0.5, 1), ("D", 0.3, 0.3, 40))]
    idx = lambda **k: PatternEffect("chase", order=k.pop("order", "left_right"), **k).pixel_indices(fx)
    assert idx() == {"A": 0, "D": 1, "B": 2, "C": 3}
    assert idx(order="right_left") == {"C": 0, "B": 1, "D": 2, "A": 3}
    assert idx(order="top_bottom") == {"C": 0, "D": 1, "B": 2, "A": 3}
    assert idx(order="name") == {"A": 0, "B": 1, "C": 2, "D": 3} and idx(order="name_desc")["D"] == 0
    assert idx(order="address") == {"B": 0, "C": 1, "A": 2, "D": 3}
    assert idx(grouping=2) == {"A": 0, "D": 0, "B": 1, "C": 1}
    assert idx(repeat=2) == {"A": 0, "D": 1, "B": 0, "C": 1}
    assert idx(origin="from_center")["B"] == 0 or idx(origin="from_center")["D"] == 0
    assert idx(origin="to_center") != idx(origin="from_center")
    assert idx(order="custom", custom_order={"A": 5, "B": 5, "C": 1, "D": 9}) == {"C": 0, "A": 1, "B": 1, "D": 2}
    a = idx(order="random_fixed"); assert a == idx(order="random_fixed") and sorted(a.values()) == [0, 1, 2, 3]


def test_sparkle_fire_meteor_snakes_jellyfish_use_time():
    fx = row(12)
    for pat in ("sparkle", "fire", "meteor", "snakes", "jellyfish"):
        e = PatternEffect(pat, [(0, 0, 0), (255, 120, 0), (255, 255, 0)], duration=2.0)
        frames = {tuple(e.evaluate(fx, t * 0.31).items()) for t in range(12)}
        assert len(frames) > 3, pat                                        # l'animazione cambia nel tempo


def test_live_cue_pattern_and_save(tmp_path):
    from showsuite.light import project as pj
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import FixtureInstance, generic_dimmer, generic_rgb
    from showsuite.light.live import LiveCue
    t = [0.0]; e = LightEngine(now=lambda: t[0])
    for i in range(3):
        e.project.patch.add(FixtureInstance(f"P{i + 1}", generic_rgb(), 1, 1 + i * 3, x=i * 0.3))
    e.project.patch.add(FixtureInstance("D1", generic_dimmer(), 1, 20, x=0.9))
    cue = LiveCue("pat", ["P1", "P2", "P3", "D1"], pattern_fx=PatternEffect("chase", [(255, 0, 0), (0, 0, 255)], duration=1.0), fade_in=0.0)
    e.project.cues.append(cue); e.live.trigger(cue); e.live.update()
    d = e.mixer.render(1); assert d[0] == 255 and d[2] == 0 and d[19] == 255      # P1 rosso; dimmer = massimo canale
    f = tmp_path / "x.showsuite-light"; pj.save(e.project, str(f)); q = pj.load(str(f))
    pf = q.cues[0].pattern_fx; assert pf.pattern == "chase" and pf.samples == [(255, 0, 0), (0, 0, 255)]
