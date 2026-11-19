from showsuite.light import properties as P
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_dimmer, generic_rgb


def make():
    e = LightEngine()
    e.project.patch.add(FixtureInstance("A", generic_rgb(), 1, 1))
    e.project.patch.add(FixtureInstance("B", generic_rgb(), 1, 4))
    e.project.patch.add(FixtureInstance("D", generic_dimmer(), 1, 10))
    return e


def test_hsb_roundtrip():
    assert P.hsb_to_rgb(0, 1, 1) == (255, 0, 0) and P.hsb_to_rgb(120, 1, 1) == (0, 255, 0)
    assert P.hsb_to_rgb(0, 0, 0.5) == (128, 128, 128)
    h, s, b = P.rgb_to_hsb(0, 0, 255)
    assert round(h) == 240 and s == 1 and b == 1


def test_set_color_and_dimmer_only_fixture():
    e = make()
    P.set_color(e, ["A", "D"], (200, 100, 0))
    out = e.mixer.render(1)
    assert (out[0], out[1], out[2]) == (200, 100, 0) and out[9] == 200


def test_dimmer_absolute_relative_and_rgb_brightness():
    e = make()
    P.set_color(e, ["A"], (200, 100, 0))
    P.set_dimmer(e, ["A"], 100)               # senza dimmer: scala la luminosità RGB mantenendo il colore
    out = e.mixer.render(1)
    assert (out[0], out[1], out[2]) == (100, 50, 0)
    P.set_dimmer(e, ["D"], 50); P.set_dimmer(e, ["D"], 30, relative=True)
    assert e.mixer.render(1)[9] == 80
    P.set_dimmer(e, ["D"], -200, relative=True)
    assert e.mixer.render(1)[9] == 0          # non scende sotto 0


def test_override_state_and_clear():
    e = make()
    assert P.override_state(e, ["A", "B"], "Red") == "none"
    e.set_value("A", "Red", 10)
    assert P.override_state(e, ["A", "B"], "Red") == "some"
    e.set_value("B", "Red", 20)
    assert P.override_state(e, ["A", "B"], "Red") == "all"
    assert P.override_state(e, ["D"], "Red") == "none"      # il fixture non ha il canale
    P.clear_override(e, ["A"], "Red")
    assert P.override_state(e, ["A", "B"], "Red") == "some" and e.mixer.render(1)[0] == 0
    P.clear_override(e, ["A", "B"])
    assert e.mixer.render(1)[3] == 0 and not any(e.values.values())
