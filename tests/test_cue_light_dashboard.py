import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from showsuite.cue.lightbridge import LocalLightBridge
from showsuite.light.control.actions import ActionRunner
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_rgb
from showsuite.ui.cue_light_dashboard import LightDashboardWindow, light_cue_names, light_fixture_names

application = QApplication.instance() or QApplication([])


def make_bridge():
    engine = LightEngine()
    engine.project.patch.add(FixtureInstance("Par 1", generic_rgb(), 1, 1))
    return LocalLightBridge(ActionRunner(engine))


def test_nomi_fixture_e_cue():
    bridge = make_bridge()
    assert light_fixture_names(bridge) == ["Par 1"]
    assert light_cue_names(bridge) == []
    assert light_fixture_names(object()) == []


def test_slider_fixture_scrive_valore():
    bridge = make_bridge()
    window = LightDashboardWindow(bridge)
    window.sliders["Par 1"].setValue(100)
    assert bridge.runner.engine.get_value("Par 1", "Red") > 0
    assert window.log.item(0).text().startswith("ok:")


def test_console_errore_e_ok():
    window = LightDashboardWindow(make_bridge())
    window.console.setText("")
    window.run_console()
    assert window.log.count() == 0
    window.console.setText("Par 1.Red 100")
    window.run_console()
    assert window.log.item(0).text() == "ok: Par 1.Red 100"
    window.console.setText("Par 1.Inesistente 10")
    window.run_console()
    assert window.log.item(0).text().startswith("errore:")


def test_cue_senza_selezione_e_clear():
    window = LightDashboardWindow(make_bridge())
    window.run_selected_cue(True)
    assert window.log.item(0).text() == "nessun cue selezionato"
    window.clear_programmer()
    assert window.log.item(0).text() == "programmer azzerato"


def test_blackout_e_master():
    window = LightDashboardWindow(make_bridge())
    window.set_master(50)
    assert window.log.item(0).text() == "ok: master 50"
    window.set_blackout(True)
    assert window.log.item(0).text() == "ok: blackout 100"


def test_bridge_remoto_solo_console():
    class Remote:
        def apply(self, command, value=None):
            self.last = command
    remote = Remote()
    window = LightDashboardWindow(remote)
    assert window.local == False
    window.console.setText("master 30")
    window.run_console()
    assert remote.last["action"] == "master"
