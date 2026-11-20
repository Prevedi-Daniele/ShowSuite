import socket
import time

import pytest

from showsuite.light.control.actions import ActionRunner
from showsuite.light.control.dmxin import DmxInput, DmxMapping, parse_artdmx, parse_sacn
from showsuite.light.dmx.drivers.artnet import build_artdmx
from showsuite.light.dmx.drivers.sacn import build_sacn
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_rgb
from showsuite.light.live import LiveCue
from showsuite.light.preset import Preset


def setup(maps):
    e = LightEngine()
    e.project.patch.add(FixtureInstance("P", generic_rgb(), 1, 1))
    e.project.cues.append(LiveCue("C", ["P"], Preset("c", {"Red": 90})))
    return e, DmxInput(ActionRunner(e), maps, artnet_port=0, sacn_port=0, host="127.0.0.1")


def test_parsers_roundtrip_and_reject_garbage():
    assert parse_artdmx(build_artdmx(0x0102, bytes([5, 6, 7, 8]), 3)) == (0x0102, bytes([5, 6, 7, 8]))
    assert parse_sacn(build_sacn(7, bytes(range(10)), b"\x01" * 16)) == (7, bytes(range(10)))
    for bad in (b"", b"Art-Net\x00\x00\x50", b"x" * 200):
        assert parse_artdmx(bad) is None and parse_sacn(bad) is None
    short = build_artdmx(1, bytes(10))[:-5]
    assert parse_artdmx(short) is None            # lunghezza dichiarata maggiore dei dati


def test_continuous_and_button_edges():
    e, d = setup([DmxMapping(1, 1, "master"), DmxMapping(1, 2, "cue", {"cue": "C"})])
    d.handle_frame(1, bytes([255, 0]))
    assert e.grand_master == 1.0 and not e.live.active           # canale a 0 all'inizio: nessun trigger
    d.handle_frame(1, bytes([128, 200]))
    assert e.grand_master == pytest.approx(128 / 255) and "C" in e.live.active   # fronte di salita
    d.handle_frame(1, bytes([128, 220]))
    assert not e.live.active["C"]["releasing"]                   # resta alto: nessun nuovo toggle
    d.handle_frame(1, bytes([128, 0]))
    assert not e.live.active["C"]["releasing"]                   # il rilascio non spegne un cue toggle
    d.handle_frame(1, bytes([128, 255]))
    assert e.live.active["C"]["releasing"]                       # nuovo fronte: toggle off


def test_bad_mapping_does_not_crash_and_other_universe_ignored():
    e, d = setup([DmxMapping(1, 1, "cue", {"cue": "Boh"}), DmxMapping(2, 1, "master")])
    d.handle_frame(1, bytes([255]))
    assert d.errors
    d.handle_frame(1, bytes([0]))   # nessun crash
    d.handle_frame(3, bytes([0]))
    assert e.grand_master == 1.0


def test_udp_artnet_and_sacn_end_to_end():
    e, d = setup([DmxMapping(1, 1, "master")])
    d.start()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(b"junk", ("127.0.0.1", d.bound["artnet"]))
        s.sendto(build_artdmx(1, bytes([51, 0])), ("127.0.0.1", d.bound["artnet"]))
        for _ in range(50):
            if e.grand_master == pytest.approx(0.2):
                break
            time.sleep(0.02)
        assert e.grand_master == pytest.approx(0.2)
        s.sendto(build_sacn(1, bytes([255]), b"\x02" * 16), ("127.0.0.1", d.bound["sacn"]))
        for _ in range(50):
            if e.grand_master == 1.0:
                break
            time.sleep(0.02)
        assert e.grand_master == 1.0
    finally:
        d.stop()
