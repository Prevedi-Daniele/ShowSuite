import pytest

from showsuite.light.beat import BeatClock
from showsuite.light.control.clocksync import PPQN, MidiClockSync
from showsuite.light.control.midi import MidiController
from showsuite.light.control.actions import ActionRunner
from showsuite.light.engine import LightEngine


class Clock:
    t = 100.0
    def __call__(self): return self.t


def feed(sync, c, bpm, n):
    for _ in range(n):
        c.t += 60.0 / (bpm * PPQN)
        sync.on_clock()


def test_bpm_follows_external_clock():
    c = Clock(); b = BeatClock(100, c); s = MidiClockSync(b, c)
    feed(s, c, 128, 60)
    assert b.bpm == pytest.approx(128, abs=0.5)
    feed(s, c, 90, 100)
    assert b.bpm == pytest.approx(90, abs=1.0)


def test_start_aligns_phase_and_keeps_grid():
    c = Clock(); b = BeatClock(120, c); s = MidiClockSync(b, c)
    c.t += 3.3                                  # fase arbitraria
    s.on_start()
    assert b.beats() == pytest.approx(0.0, abs=1e-6)
    feed(s, c, 120, 24 * 4 + 1)                 # 4 battute
    assert b.beats() == pytest.approx(4.0, abs=0.1) or b.beats() == pytest.approx(4.0 + 1 / 24, abs=0.1)
    assert abs(b.beats() - round(b.beats())) < 0.1


def test_pause_resets_estimate_and_disable():
    c = Clock(); b = BeatClock(100, c); s = MidiClockSync(b, c)
    feed(s, c, 140, 40)
    c.t += 5                                    # silenzio: il master si ferma
    feed(s, c, 110, 40)
    assert b.bpm == pytest.approx(110, abs=1.0)
    s.enabled = False
    feed(s, c, 200, 60)
    assert b.bpm == pytest.approx(110, abs=1.0)


def test_midi_controller_routes_clock_messages():
    class Msg:
        def __init__(self, type): self.type = type
    e = LightEngine(); m = MidiController(ActionRunner(e))
    calls = []
    class Fake:
        def on_clock(self): calls.append("c")
        def on_start(self): calls.append("s")
        def on_stop(self): calls.append("x")
        def on_continue(self): calls.append("k")
    m.clock = Fake()
    for t in ("clock", "start", "continue", "stop"):
        m._on_message(Msg(t))
    assert calls == ["c", "s", "k", "x"]
