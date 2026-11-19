import pytest

from showsuite.light.dmx import Mixer, OutputManager, Universe
from showsuite.light.dmx.drivers.artnet import build_artdmx
from showsuite.light.dmx.drivers.base import OutputDriver
from showsuite.light.dmx.drivers.sacn import build_sacn, multicast_address
from showsuite.light.fixtures import (ChannelDef, FixtureInstance, FixtureProfile, Patch,
                                      PatchError, generic_dimmer, generic_rgb)


def test_universe_clamp_and_range():
    u = Universe(1)
    u.set(1, 300); u.set(512, -5)
    assert u.get(1) == 255 and u.get(512) == 0
    with pytest.raises(ValueError):
        u.set(0, 1)
    with pytest.raises(ValueError):
        u.set(513, 1)


def test_patch_overlap_and_free():
    p = Patch()
    p.add(FixtureInstance("A", generic_rgb(), 1, 1))
    with pytest.raises(PatchError):
        p.add(FixtureInstance("B", generic_rgb(), 1, 3))
    p.add(FixtureInstance("C", generic_rgb(), 2, 3))  # altro universo: ok
    assert p.next_free(1, 3) == 4
    with pytest.raises(PatchError):
        p.add(FixtureInstance("D", generic_rgb(), 1, 511))


def test_fixture_write_16bit():
    prof = FixtureProfile("X", "Mover", "m", (ChannelDef("Dimmer"), ChannelDef("Pan", fine=True)))
    fx = FixtureInstance("M", prof, 1, 10)
    u = Universe(1)
    fx.write({"Dimmer": 200, "Pan": 0x1234}, u)
    assert (u.get(10), u.get(11), u.get(12)) == (200, 0x12, 0x34)
    assert fx.end_address == 12


def test_mixer_priority():
    m = Mixer()
    low, high = m.add_layer(1), m.add_layer(10)
    low.set(1, 1, 100); low.set(1, 2, 50)
    high.set(1, 1, 200)
    out = m.render(1)
    assert out[0] == 200 and out[1] == 50
    high.release(1, 1)
    assert m.render(1)[0] == 100


def test_artdmx_packet():
    pkt = build_artdmx(0x0102, bytes([7] * 3), sequence=5)
    assert pkt[:8] == b"Art-Net\x00" and pkt[8:10] == b"\x00\x50"
    assert pkt[12] == 5 and pkt[14] == 0x02 and pkt[15] == 0x01
    assert pkt[16:18] == b"\x00\x04" and len(pkt) == 18 + 4  # padding a lunghezza pari


def test_sacn_packet_layout():
    pkt = build_sacn(1, bytes(512), b"\x01" * 16, sequence=9)
    assert len(pkt) == 638
    assert int.from_bytes(pkt[16:18], "big") == 0x7000 | 622
    assert int.from_bytes(pkt[38:40], "big") == 0x7000 | 600
    assert int.from_bytes(pkt[115:117], "big") == 0x7000 | 523
    assert pkt[111] == 9 and pkt[108] == 100
    assert int.from_bytes(pkt[113:115], "big") == 1  # universo
    assert int.from_bytes(pkt[123:125], "big") == 513 and pkt[125] == 0  # count, start code
    assert multicast_address(0x0102) == "239.255.1.2"


class Fake(OutputDriver):
    def __init__(self, fail=False):
        self.sent, self.fail, self.opened = [], fail, False
    def open(self): self.opened = True
    def send(self, universe, data):
        if self.fail:
            raise OSError("scollegato")
        self.sent.append((universe, data))
    def close(self): self.opened = False


def test_output_manager_multi_interface_and_fault_isolation():
    m = Mixer(); l = m.add_layer(1); l.set(1, 1, 255); l.set(2, 1, 9)
    om = OutputManager(m)
    a, b, bad = Fake(), Fake(), Fake(fail=True)
    om.route(1, a); om.route(1, b); om.route(2, a); om.route(1, bad)
    om.tick()
    assert [u for u, _ in a.sent] == [1, 2] and b.sent[0][1][0] == 255
    assert len(om.errors) == 1 and om.errors[0][0] is bad
