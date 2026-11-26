"""Cablaggio dei servizi di un workspace: API OSC QLab, uscite, trigger, audio, video e ponte Light.

`Services` non dipende da Qt: la finestra lo crea e lo avvia, i test lo usano direttamente.
Tutto ciò che tocca hardware (server di rete, scheda audio, porte MIDI) parte solo con `start()` e solo se richiesto."""
from __future__ import annotations

import datetime

from .engine import ActionHandler, Runtime
from .model import TYPE_AUDIO, TYPE_CAMERA, TYPE_TEXT, TYPE_VIDEO
from .outputs import OutputHub
from .qlab_api import QLabApi
from .triggers import TriggerManager


class ChainHandler(ActionHandler):
    """Inoltra ogni evento a più handler (per i tipi serviti da audio e video insieme)."""

    def __init__(self, handlers: list[ActionHandler]):
        self.handlers = handlers

    def start(self, runtime, state):
        for handler in self.handlers:
            handler.start(runtime, state)

    def stop(self, runtime, state, hard):
        for handler in self.handlers:
            handler.stop(runtime, state, hard)

    def panic(self, runtime, state, duration):
        for handler in self.handlers:
            handler.panic(runtime, state, duration)

    def pause(self, runtime, state):
        for handler in self.handlers:
            handler.pause(runtime, state)

    def resume(self, runtime, state):
        for handler in self.handlers:
            handler.resume(runtime, state)

    def load(self, runtime, cue, seconds):
        for handler in self.handlers:
            handler.load(runtime, cue, seconds)

    def update(self, runtime, state):
        for handler in self.handlers:
            handler.update(runtime, state)

    def parameters_changed(self, runtime, cue, changes):
        for handler in self.handlers:
            handler.parameters_changed(runtime, cue, changes)


class MidiInputListener:
    """Ascolta una porta MIDI reale tramite mido e inoltra i messaggi ai trigger. Mai provato su hardware."""

    def __init__(self, port_name: str, callback):
        import mido
        self.mido = mido
        self.port = mido.open_input(port_name if port_name != "" else None, callback=self._receive)
        self.callback = callback

    def _receive(self, message) -> None:
        self.callback(bytes(message.bytes()))

    def close(self) -> None:
        self.port.close()


class Services:
    def __init__(self, runtime: Runtime, osc_port: int | None = None, audio_device=None, use_audio_device: bool = False,
                 midi_backend=None, midi_input_port: str | None = None, live_network: bool = False,
                 video_sink=None, light_bridge=None, osc_from_workspace: bool = False):
        self.runtime = runtime
        self.osc_port = osc_port
        self.osc_from_workspace = osc_from_workspace
        self.audio_device = audio_device
        self.use_audio_device = use_audio_device
        self.midi_input_port = midi_input_port
        self.api = QLabApi([runtime])
        self.hub = OutputHub(runtime, self.api, midi_backend, live_network)
        self.hub.install()
        self.triggers = TriggerManager(runtime)
        self.mixer = None
        self.compositor = None
        self.osc_server = None
        self.midi_listener = None
        self.errors: list[str] = []
        self._install_audio_video(video_sink)
        if light_bridge is not None:
            from .lightbridge import install_light_bridge
            install_light_bridge(runtime, light_bridge)

    def _install_audio_video(self, video_sink) -> None:
        mixer = None
        compositor = None
        try:
            from .audio import AudioMixer
            mixer = AudioMixer(self.runtime)
        except ImportError as error:
            self.errors.append("audio non disponibile: " + str(error))
        try:
            from .video import VideoCompositor
            compositor = VideoCompositor(self.runtime, video_sink)
        except ImportError as error:
            self.errors.append("video non disponibile: " + str(error))
        if mixer is not None:
            mixer.install()
        if compositor is not None:
            compositor.install()
        if mixer is not None and compositor is not None:
            self.runtime.register_handler(TYPE_VIDEO, ChainHandler([mixer, compositor]))
        self.mixer = mixer
        self.compositor = compositor

    # --- ciclo di vita ---
    def start(self) -> None:
        self.start_osc()
        self._start_devices()

    def start_osc(self) -> None:
        ports = self.osc_ports()
        if ports is not None:
            from .osc import OscServer
            self.osc_server = OscServer(self.api.handle, port=ports[0], reply_port=ports[1], plain_port=ports[2])
            try:
                self.osc_server.start()
            except OSError as error:
                self.errors.append("server OSC non avviato: " + str(error))
                self.osc_server = None

    def restart_osc(self) -> None:
        """Riavvia il server OSC con le impostazioni correnti (dopo la modifica delle impostazioni)."""
        if self.osc_server is not None:
            self.osc_server.stop()
            self.osc_server = None
        self.start_osc()

    def _start_devices(self) -> None:
        if self.use_audio_device == True and self.mixer is not None:
            try:
                self.mixer.open_stream(self.audio_device)
            except Exception as error:
                self.errors.append("uscita audio non aperta: " + str(error))
        if self.midi_input_port is not None:
            try:
                self.midi_listener = MidiInputListener(self.midi_input_port, self.triggers.midi_in)
            except Exception as error:
                self.errors.append("ingresso MIDI non aperto: " + str(error))

    def osc_ports(self) -> tuple[int, int, int] | None:
        """Porte (principale, risposte, testo semplice) o None se il server OSC non va avviato.

        Con `osc_from_workspace` valgono le impostazioni del workspace (osc_access, osc_port, osc_reply_port,
        osc_plain_port); altrimenti `osc_port` esplicito (le altre due restano ai valori predefiniti)."""
        if self.osc_from_workspace == True:
            settings = self.runtime.workspace.settings
            if settings.get("osc_access", True) == False:
                return None
            return (int(settings.get("osc_port", 53000)), int(settings.get("osc_reply_port", 53001)),
                    int(settings.get("osc_plain_port", 53535)))
        if self.osc_port is not None:
            return (self.osc_port, 53001, 53535)
        return None

    def stop(self) -> None:
        if self.osc_server is not None:
            self.osc_server.stop()
            self.osc_server = None
        if self.mixer is not None:
            self.mixer.close_stream()
        if self.midi_listener is not None:
            self.midi_listener.close()
            self.midi_listener = None

    # --- chiamato dal timer della finestra ---
    def tick(self, now: datetime.datetime | None = None) -> None:
        self.triggers.wall_clock_tick(now)
        if self.compositor is not None and self.compositor.sink is not None:
            if self._has_video_layers() == True:
                self.compositor.render_routes()

    def _has_video_layers(self) -> bool:
        return len(self.compositor.active_layers()) > 0
