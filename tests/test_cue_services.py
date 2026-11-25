import os
import socket

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_NETWORK, TYPE_VIDEO, Workspace
from showsuite.cue.osc import encode_message
from showsuite.cue.services import ChainHandler, Services


def test_catena_video_audio_e_compositor():
    workspace = Workspace("S")
    runtime = Runtime(workspace, ManualClock())
    services = Services(runtime)
    handler = runtime.handlers[TYPE_VIDEO]
    assert isinstance(handler, ChainHandler)
    assert len(handler.handlers) == 2
    assert TYPE_NETWORK in runtime.handlers


def test_server_osc_avviato_dai_servizi_controlla_il_workspace():
    workspace = Workspace("S")
    cue = workspace.new_cue(TYPE_NETWORK)
    cue.number = "7"
    cue.duration = 30.0
    workspace.settings["passcodes"] = [{"passcode": "", "view": True, "edit": True, "control": True}]
    runtime = Runtime(workspace, ManualClock())
    services = Services(runtime, osc_port=0)
    services.start()
    assert services.osc_server is not None
    udp_port = services.osc_server.bound_ports()[0]
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto(encode_message("/cue/7/start", []), ("127.0.0.1", udp_port))
    import time
    deadline = time.time() + 2
    while time.time() < deadline and runtime.states.get(cue.unique_id) is None:
        time.sleep(0.02)
    services.stop()
    assert cue.unique_id in runtime.states


def test_finestra_inoltra_hotkey_ai_trigger():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_window import CueWindow
    QApplication.instance() or QApplication([])
    workspace = Workspace("S")
    cue = workspace.new_cue(TYPE_NETWORK)
    cue.params["message"] = "/x"
    cue.triggers["hotkey"] = "F5"
    runtime = Runtime(workspace, ManualClock())
    window = CueWindow(workspace, runtime)
    window.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_F5, Qt.NoModifier))
    assert cue.unique_id in runtime.states


def test_sostituzione_workspace_ricrea_i_servizi():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_window import CueWindow
    QApplication.instance() or QApplication([])
    workspace = Workspace("S")
    window = CueWindow(workspace, Runtime(workspace, ManualClock()))
    old = window.services
    window._replace_workspace(Workspace("Altro"))
    assert window.services is not old
    assert window.services.runtime is window.runtime
    assert TYPE_NETWORK in window.runtime.handlers
