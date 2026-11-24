import json
import os

import pytest

from showsuite.light import project as pj
from showsuite.light import properties as P
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance
from showsuite.light.fixtures.ofl import parse_ofl

DOC = {
    "name": "Spot", "availableChannels": {
        "Dimmer": {"capability": {"type": "Intensity"}},
        "Shutter": {"capabilities": [
            {"dmxRange": [0, 9], "type": "ShutterStrobe", "shutterEffect": "Closed"},
            {"dmxRange": [10, 19], "type": "ShutterStrobe", "shutterEffect": "Open"},
            {"dmxRange": [20, 99], "type": "ShutterStrobe", "shutterEffect": "Strobe"}]},
        "Pan": {"capability": {"type": "Pan"}}, "Tilt": {"capability": {"type": "Tilt"}},
        "Zoom": {"capability": {"type": "Zoom"}},
        "Gobo": {"capabilities": [
            {"dmxRange": [0, 9], "type": "WheelSlot", "wheel": "Gobo Wheel", "slotNumber": 1},
            {"dmxRange": [10, 19], "type": "WheelSlot", "wheel": "Gobo Wheel", "slotNumber": 2}]},
        "Color": {"capabilities": [
            {"dmxRange": [0, 9], "type": "WheelSlot", "wheel": "Color Wheel", "slotNumber": 1},
            {"dmxRange": [10, 19], "type": "ColorPreset", "comment": "Rosso"}]},
    },
    "modes": [{"name": "m", "channels": ["Dimmer", "Shutter", "Pan", "Tilt", "Zoom", "Gobo", "Color"]}],
}


def setup():
    (prof,) = parse_ofl(DOC, "X")
    e = LightEngine()
    e.project.patch.add(FixtureInstance("S1", prof, 1, 1))
    e.project.patch.add(FixtureInstance("S2", prof, 1, 20))
    return e, prof


def test_ofl_kinds_and_caps():
    _, prof = setup()
    assert [c.kind for c in prof.channels] == ["intensity", "shutter", "pan", "tilt", "zoom", "gobo_wheel", "color_wheel"]
    assert P.available_properties(prof) == ["dimmer", "color_wheel", "gobo_wheel", "shutter", "position", "zoom"]
    assert prof.channel_of_kind("shutter").caps[1] == (10, 19, "ShutterStrobe", "Open")


def test_shutter_wheel_position_zoom_and_dots():
    e, prof = setup()
    assert P.set_shutter(e, ["S1", "S2"], "open") == 2 and e.mixer.render(1)[1] == 14
    P.set_shutter(e, ["S1"], "strobe", 1.0); assert e.mixer.render(1)[1] == 99
    P.set_shutter(e, ["S1"], "closed"); assert e.mixer.render(1)[1] == 4
    assert P.set_slot(e, ["S1"], "gobo_wheel", 1) == 1 and e.mixer.render(1)[5] == 14
    assert P.set_slot(e, ["S1"], "gobo_wheel", 5) == 0                      # slot inesistente
    assert [l for _, l in P.wheel_slots(prof, "color_wheel")] == ["1", "Rosso"]
    P.set_position(e, ["S1"], pan=0.5, tilt=1.0)
    assert e.mixer.render(1)[2] == 128 and e.mixer.render(1)[3] == 255
    P.set_simple(e, ["S1"], "zoom", 0.5); assert e.mixer.render(1)[4] == 128
    assert P.property_state(e, ["S1", "S2"], "shutter") == "all"            # entrambi impostati sopra
    P.clear_property(e, ["S1"], "shutter")
    assert P.property_state(e, ["S1"], "shutter") == "none" and e.mixer.render(1)[1] == 0
    assert P.property_state(e, ["S1", "S2"], "shutter") == "some"
    assert P.property_state(e, ["S1", "S2"], "position") == "some"
    P.clear_property(e, ["S1", "S2"], "position")
    assert P.property_state(e, ["S1", "S2"], "position") == "none"


def test_generic_dimmer_property_for_rgb_and_roundtrip(tmp_path):
    from showsuite.light.fixtures import generic_rgb
    e = LightEngine()
    e.project.patch.add(FixtureInstance("R", generic_rgb(), 1, 1))
    assert P.available_properties(generic_rgb()) == ["dimmer", "color"]
    assert P.property_channels(generic_rgb(), "dimmer") == ["Red", "Green", "Blue"]
    (prof,) = parse_ofl(DOC, "X")
    p = pj.Project("T"); p.patch.add(FixtureInstance("S", prof, 1, 1))
    f = tmp_path / "t.showsuite-light"; pj.save(p, str(f)); q = pj.load(str(f))
    assert q.patch.find("S").profile.channel_of_kind("shutter").caps[0][3] == "Closed"
    assert q.patch.find("S").profile.channel_of_kind("gobo_wheel") is not None


def test_position_pad_degrees():
    import os; os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from showsuite.ui.position_pad import PositionPad
    got = []
    pad = PositionPad(lambda a, b: got.append((a, b)), 540, 270)
    pad.spins[0].setValue(135.0); pad.spins[1].setValue(-67.5)
    assert got[0][0] == 0.75 and got[1][1] == 0.25
    pad.pad.moved.emit(0.5, 0.5); assert pad.spins[0].value() == 0


def test_copy_paste_reset():
    from showsuite.light import project as pj, properties as P
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    pr = pj.Project("C")
    for i in range(2):
        pr.patch.add(FixtureInstance(f"F{i}", generic_rgb(), 1, 1 + i * 3))
    e = LightEngine(pr); P.set_color(e, ["F0"], (255, 0, 0))
    assert P.paste_properties(e, ["F1"], P.copy_properties(e, "F0")) > 0
    assert e.values["F1"] == e.values["F0"]
    P.reset_to_default(e, ["F1"]); assert "F1" not in e.values


def test_shift_letter_selects_property():
    import os; os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from showsuite.light import project as pj
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    from showsuite.ui.preview import PreviewWidget
    p = pj.Project("K"); p.patch.add(FixtureInstance("F", generic_rgb(), 1, 1))
    w = PreviewWidget(LightEngine(p)); got = []; w.property_key.connect(got.append)
    w.set_selection(["F"]); QTest.keyClick(w, Qt.Key_C, Qt.ShiftModifier)
    assert got == ["C"]


def test_fog_speed_custom_properties():
    from showsuite.light import project as pj, properties as P
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import ChannelDef, FixtureInstance, FixtureProfile
    prof = FixtureProfile("A", "Fogger", "3", (ChannelDef("Fog", kind="fog"), ChannelDef("Spd", kind="speed"), ChannelDef("Boh")))
    assert P.available_properties(prof) == ["fog", "speed", "custom"]
    p = pj.Project("F"); p.patch.add(FixtureInstance("G", prof, 1, 1)); e = LightEngine(p)
    P.set_simple(e, ["G"], "fog", 1.0); P.set_channel(e, ["G"], "Boh", 0.5)
    assert e.values["G"] == {"Fog": 255, "Boh": 128}
    assert P.property_state(e, ["G"], "custom") == "all"


def test_onoff_property():
    from showsuite.light import project as pj, properties as P
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import ChannelDef, FixtureInstance, FixtureProfile
    prof = FixtureProfile("A", "Switch", "1", (ChannelDef("Power", kind="onoff"),))
    assert P.available_properties(prof) == ["onoff"]
    p = pj.Project("O"); p.patch.add(FixtureInstance("S", prof, 1, 1)); e = LightEngine(p)
    P.set_simple(e, ["S"], "onoff", 1.0); assert e.values["S"]["Power"] == 255
    P.set_simple(e, ["S"], "onoff", 0.0); assert e.values["S"]["Power"] == 0
