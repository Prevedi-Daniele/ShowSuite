import pytest

from showsuite.light.beat import BeatClock
from showsuite.light.effects import Effect
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_dimmer, generic_rgb
from showsuite.light.live import LiveCue
from showsuite.light.preset import Preset


class Clock:
    t = 0.0
    def __call__(self): return self.t


def test_tap_tempo():
    c = Clock(); b = BeatClock(100, c)
    for _ in range(5):
        b.tap(); c.t += 0.5
    assert b.bpm == pytest.approx(120, abs=0.5)
    with pytest.raises(ValueError):
        b.set_bpm(5)


def test_effect_waves_and_fan():
    e = Effect("Dimmer", "square", beats_per_cycle=1)
    assert e.value(0.0) == 255 and e.value(0.6) == 0
    e = Effect("Dimmer", "saw", fan=1.0)
    v = e.evaluate(["a", "b", "c", "d"], 0.0)
    assert [v[k] for k in "abcd"] == [0, 64, 128, 191]
    with pytest.raises(ValueError):
        Effect("Dimmer", "boh").value(0)


def make():
    c = Clock()
    e = LightEngine(now=c)
    for i in range(2):
        e.project.patch.add(FixtureInstance(f"P{i}", generic_rgb(), 1, 1 + 3 * i))
    return e, c


def test_cue_fade_and_release():
    e, c = make()
    cue = LiveCue("Rosso", ["P0", "P1"], Preset("r", {"Red": 200}), fade_in=2.0, fade_out=1.0)
    e.live.trigger(cue)
    e.live.update(); assert e.mixer.render(1)[0] == 0
    c.t = 1.0; e.live.update(); assert e.mixer.render(1)[0] == 100
    c.t = 2.0; e.live.update(); assert e.mixer.render(1)[0] == 200 and e.mixer.render(1)[3] == 200
    e.live.trigger(cue)  # toggle: release
    c.t = 2.5; e.live.update(); assert e.mixer.render(1)[0] == 100
    c.t = 4.0; e.live.update(); assert e.mixer.render(1)[0] == 0 and not e.live.active


def test_priority_and_skip_missing_channel():
    e, c = make()
    e.project.patch.add(FixtureInstance("D", generic_dimmer(), 1, 10))
    low = LiveCue("low", ["P0"], Preset("a", {"Red": 50}), priority=5)
    high = LiveCue("high", ["P0", "D"], Preset("b", {"Red": 250}), priority=20)  # D non ha Red
    e.live.trigger(low); e.live.trigger(high); e.live.update()
    assert e.mixer.render(1)[0] == 250 and e.mixer.render(1)[9] == 0
    e.live.trigger(high); e.live.update()
    assert e.mixer.render(1)[0] == 50


def test_effect_cue_follows_beat():
    e, c = make()
    e.beat.set_bpm(60)  # 1 battuta al secondo
    cue = LiveCue("chase", ["P0", "P1"], effects=[Effect("Red", "saw", fan=0.5)])
    e.live.trigger(cue)
    c.t = 0.5; e.live.update()
    out = e.mixer.render(1)
    assert out[0] == 128 and out[3] == round(255 * 0.75)
