from showsuite.light import project as pj
from showsuite.light.control.feedback import MidiFeedback, OscFeedback
from showsuite.light.control.midi import MidiMapping
from showsuite.light.control.osc import parse_osc
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_dimmer
from showsuite.light.live import LiveCue


def mk():
    p = pj.Project("F"); p.patch.add(FixtureInstance("D", generic_dimmer(), 1, 1))
    p.cues = [LiveCue("A", ["D"], pj.Preset("x", {"D": {"Dimmer": 255}}) if False else None)]
    return LightEngine(p)


def test_osc_feedback_only_changes():
    e = mk(); sent = []
    fb = OscFeedback(lambda h, p, d: sent.append((h, p, parse_osc(d)[0])))
    assert fb.poll(e) == 0                       # nessun client
    fb.add_target("1.2.3.4", 9000)
    assert fb.poll(e) > 0 and ("1.2.3.4", 9000, ("/cue/A", [0.0])) in sent
    sent.clear(); assert fb.poll(e) == 0 and not sent
    e.live.active["A"] = {}; assert fb.poll(e) == 1 and sent[0][2] == ("/cue/A", [1.0])
    sent.clear(); e.blackout = True; fb.poll(e); assert ("/blackout", [1.0]) == sent[0][2]


def test_midi_feedback_leds():
    e = mk(); out = []
    fb = MidiFeedback(lambda *a: out.append(a))
    maps = [MidiMapping("note", 0, 36, "cue", {"cue": "A"}), MidiMapping("cc", 0, 1, "master")]
    assert fb.poll(e, maps) == 1 and out[-1] == ("note", 0, 36, 0)
    e.live.active["A"] = {}; fb.poll(e, maps); assert out[-1] == ("note", 0, 36, 127)
    assert fb.poll(e, maps) == 0
