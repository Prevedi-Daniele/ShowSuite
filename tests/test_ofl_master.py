import pytest

from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_dimmer, generic_rgb
from showsuite.light.fixtures.ofl import OflImportError, parse_ofl

DOC = {
    "name": "Mover X",
    "availableChannels": {
        "Dimmer": {"defaultValue": 0, "capability": {"type": "Intensity"}},
        "Pan": {"fineChannelAliases": ["Pan fine"], "defaultValue": "50%", "capability": {"type": "Pan"}},
        "Red": {"capability": {"type": "ColorIntensity", "color": "Red"}},
        "Mode": {"capabilities": [{"dmxRange": [0, 255], "type": "NoFunction",
                                   "switchChannels": {"Speed / Sens": "Speed"}}]},
    },
    "modes": [
        {"name": "6ch", "channels": ["Dimmer", "Pan", "Pan fine", None, "Red", "Speed / Sens"]},
        {"name": "bad", "channels": [{"insert": "matrixChannels"}]},
    ],
}


def test_parse_ofl_fine_null_switching():
    doc = dict(DOC, modes=DOC["modes"][:1])
    (p,) = parse_ofl(doc, "Acme")
    assert p.manufacturer == "Acme" and p.footprint == 6
    pan = next(c for c in p.channels if c.name == "Pan")
    assert pan.fine and pan.default == 32768 and p.channel_of_kind("intensity").name == "Dimmer"
    assert p.channel_of_kind("red") is not None
    assert any(c.name.startswith("(vuoto") for c in p.channels)


def test_parse_ofl_errors():
    with pytest.raises(OflImportError):
        parse_ofl(DOC)            # la modalità "bad" usa canali matrice
    with pytest.raises(OflImportError):
        parse_ofl({"x": 1})


def test_grand_master_blackout_freeze():
    e = LightEngine()
    e.project.patch.add(FixtureInstance("D", generic_dimmer(), 1, 1))
    e.project.patch.add(FixtureInstance("P", generic_rgb(), 1, 10))
    e.set_value("D", "Dimmer", 200); e.set_value("P", "Red", 100); e.set_value("P", "Blue", 50)
    e.grand_master = 0.5
    out = e.process(1, e.mixer.render(1))
    assert out[0] == 100 and out[9] == 50 and out[11] == 25
    e.blackout = True
    assert e.process(1, e.mixer.render(1))[0] == 0
    e.blackout = False; e.grand_master = 1.0
    e.set_freeze(True)
    assert e.process(1, e.mixer.render(1))[0] == 200
    e.set_value("D", "Dimmer", 10)
    assert e.process(1, e.mixer.render(1))[0] == 200   # congelato
    e.set_freeze(False)
    assert e.process(1, e.mixer.render(1))[0] == 10
