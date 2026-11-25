import pytest

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.lightbridge import LocalLightBridge, RemoteLightBridge, install_light_bridge, parse_command
from showsuite.cue.model import TYPE_LIGHT, Workspace
from showsuite.cue.outputs import OutputHub
from showsuite.cue.qlab_api import QLabApi


def make_light():
    from showsuite.light.control.actions import ActionRunner
    from showsuite.light.engine import LightEngine
    engine = LightEngine()
    return engine, ActionRunner(engine)


def test_parse_command():
    assert parse_command("cue Rosso") == {"kind": "cue", "name": "Rosso", "on": True}
    assert parse_command("release Rosso")["on"] == False
    assert parse_command("Front Wash.Red 50")["fixture"] == "Front Wash"
    assert parse_command("Front 25")["channel"] == ""
    assert parse_command("blackout 100") == {"kind": "plain", "action": "blackout", "value": 1.0}
    assert parse_command("osc /master 0.5")["address"] == "/master"
    with pytest.raises(ValueError):
        parse_command("")


def test_ponte_locale_regola_canale_con_fade():
    pytest.importorskip("PySide6")
    engine, runner = make_light()
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    engine.project.patch.add(FixtureInstance("Par 1", generic_rgb(), 1, 1))
    workspace = Workspace("L")
    runtime = Runtime(workspace, ManualClock())
    install_light_bridge(runtime, LocalLightBridge(runner))
    cue = workspace.new_cue(TYPE_LIGHT)
    cue.params["commands"] = ["Par 1.Red 100"]
    cue.duration = 2.0
    cue.params["curve"] = {"type": "linear", "intensity": 0.5, "rising": [], "falling": []}
    runtime.start_cue(cue)
    runtime.advance(1.0)
    assert 120 <= engine.get_value("Par 1", "Red") <= 135
    runtime.advance(1.2)
    assert engine.get_value("Par 1", "Red") == 255


def test_ponte_remoto_invia_osc():
    workspace = Workspace("R")
    runtime = Runtime(workspace, ManualClock())
    hub = OutputHub(runtime, QLabApi([runtime]))
    workspace.patches["network"] = [{"name": "Light", "kind": "udp", "host": "10.0.0.9", "port": 21600}]
    install_light_bridge(runtime, RemoteLightBridge(hub, 1))
    cue = workspace.new_cue(TYPE_LIGHT)
    cue.params["commands"] = ["cue Rosso", "master 50"]
    runtime.start_cue(cue)
    sent = [item[3] for item in hub.network_sent]
    assert sent[0].startswith(b"/cue/Rosso") and sent[1].startswith(b"/master")
