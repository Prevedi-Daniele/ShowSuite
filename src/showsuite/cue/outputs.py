"""Uscite di protocollo: Network (OSC/UDP/TCP), MIDI (voce/MSC/SysEx), file MIDI, Timecode (MTC/LTC).

`OutputHub` astrae le porte reali. Senza backend configurati registra solo i messaggi (modalità test/dry-run).
NON provato su hardware: porte MIDI reali richiedono `mido` + `python-rtmidi`; LTC richiede un backend audio."""
from __future__ import annotations

import os
import re
import socket

from . import curves
from .engine import ActionHandler, CueState, Runtime
from .model import (TYPE_MIDI, TYPE_MIDI_FILE, TYPE_NETWORK, TYPE_TIMECODE, Cue)
from .osc import MemoryClient, encode_message, parse_plain_text
from .playback import INFINITE
from .protocols import (MSC_COMMANDS, TIMECODE_FORMATS, frames_per_second, ltc_encode_frame, msc_message,
                        mtc_full_frame, mtc_quarter_frames, parse_midi_file, pitch_bend_message,
                        seconds_to_timecode, sysex_from_text, timecode_to_seconds, voice_message, parse_timecode_text)

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")


class MidiBackend:
    def send(self, device: str, data: bytes) -> None:
        raise NotImplementedError


class MidoBackend(MidiBackend):
    """Backend MIDI reale tramite mido (import pigro). Mai provato su hardware."""

    def __init__(self):
        import mido
        self.mido = mido
        self.ports: dict = {}

    def send(self, device: str, data: bytes) -> None:
        port = self.ports.get(device)
        if port is None:
            port = self.mido.open_output(device if device != "" else None)
            self.ports[device] = port
        if data[0] == 0xF0:
            port.send(self.mido.Message("sysex", data=list(data[1:-1])))
        else:
            port.send(self.mido.Message.from_bytes(list(data)))


class OutputHub:
    def __init__(self, runtime: Runtime, api=None, midi_backend: MidiBackend | None = None, live_network: bool = False):
        self.runtime = runtime
        self.api = api
        self.midi_backend = midi_backend
        self.live_network = live_network
        self.midi_sent: list[tuple[str, bytes]] = []
        self.network_sent: list[tuple[str, str, int, bytes]] = []
        self.ltc_frames: list[tuple] = []
        self.tcp_connections: dict = {}
        self.udp_socket: socket.socket | None = None

    def install(self) -> None:
        self.runtime.register_handler(TYPE_NETWORK, NetworkHandler(self))
        self.runtime.register_handler(TYPE_MIDI, MidiHandler(self))
        self.runtime.register_handler(TYPE_MIDI_FILE, MidiFileHandler(self))
        self.runtime.register_handler(TYPE_TIMECODE, TimecodeHandler(self))

    def _overridden(self, key: str) -> bool:
        return self.runtime.workspace.settings["overrides"].get(key, True) == False

    # --- patch ---
    def midi_patch(self, number: int) -> dict:
        patches = self.runtime.workspace.patches["midi"]
        if 1 <= number <= len(patches):
            return patches[number - 1]
        return {"name": "", "device": ""}

    def network_patch(self, number: int) -> dict | None:
        patches = self.runtime.workspace.patches["network"]
        if 1 <= number <= len(patches):
            return patches[number - 1]
        return None

    # --- invio ---
    def send_midi(self, patch_number: int, data: bytes, override_key: str = "midiOutput") -> None:
        if self._overridden(override_key):
            return
        patch = self.midi_patch(patch_number)
        self.midi_sent.append((patch.get("device", ""), data))
        if self.midi_backend is not None:
            self.midi_backend.send(patch.get("device", ""), data)

    def send_network(self, patch_number: int, kind: str, payload: bytes, address: str = "",
                     arguments: list | None = None) -> None:
        patch = self.network_patch(patch_number)
        if patch is None:
            return
        host = patch.get("host", "127.0.0.1")
        port = int(patch.get("port", 53000))
        local = host in LOCAL_HOSTS
        if self._overridden("networkLocalOutput" if local else "networkExternalOutput"):
            return
        settings = self.runtime.workspace.settings
        self.network_sent.append((kind, host, port, payload))
        if kind == "osc":
            self.runtime.logs.add("osc_out", "%s:%d %s %s" % (host, port, address, " ".join(str(item) for item in (arguments or []))))
        if local == True and self.api is not None and kind == "osc" and port == int(settings.get("osc_port", 53000)):
            # localhost sull'OSC del workspace stesso: non esce dall'applicazione
            from .qlab_api import Session
            session = Session()
            session.permissions[self.runtime.workspace.workspace_id] = {"view", "edit", "control"}
            self.api.process(address, arguments or [], session, only=self.runtime)
            return
        if self.live_network == False:
            return
        if patch.get("kind", kind) == "tcp" or kind == "tcp":
            connection = self.tcp_connections.get((host, port))
            if connection is None:
                connection = socket.create_connection((host, port), timeout=2.0)
                self.tcp_connections[(host, port)] = connection
            connection.sendall(payload)
        else:
            if self.udp_socket is None:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.sendto(payload, (host, port))


QUERY_PATTERN = re.compile(r"#(.+?)#")


def substitute_queries(text: str, api, runtime: Runtime) -> str:
    if api is None:
        return text

    def replace(match) -> str:
        pieces = match.group(1).split(" ", 1)
        arguments = parse_plain_text("/x " + pieces[1])[1] if len(pieces) > 1 else []
        value = api.query(pieces[0], arguments, runtime)
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        return "" if value is None else str(value)

    return QUERY_PATTERN.sub(replace, text)


def unescape_text(text: str) -> bytes:
    return text.encode("utf-8").decode("unicode_escape").encode("latin-1", errors="replace")


class NetworkHandler(ActionHandler):
    def __init__(self, hub: OutputHub):
        self.hub = hub

    def _format_message(self, runtime: Runtime, cue: Cue, text: str, values: list | None) -> tuple[str, bytes, list, str]:
        text = substitute_queries(text, self.hub.api, runtime)
        if values is not None:
            for index, value in enumerate(values):
                text = text.replace("$%d" % (index + 1), self._format_number(cue, value))
        kind = cue.params.get("message_kind", "osc")
        if kind == "osc":
            address, arguments = parse_plain_text(text)
            return address, encode_message(address, arguments), arguments, "osc"
        return "", unescape_text(text), [], kind

    @staticmethod
    def _format_number(cue: Cue, value: float) -> str:
        if int(cue.params.get("number_type", 1)) == 0:
            return str(int(round(value)))
        text = ("%.6f" % value).rstrip("0").rstrip(".")
        return text if "." in text else text + ".0"

    def _send(self, runtime: Runtime, cue: Cue, values: list | None) -> None:
        address, payload, arguments, kind = self._format_message(runtime, cue, str(cue.params.get("message", "")), values)
        self.hub.send_network(int(cue.params.get("network_patch", 1)), kind, payload, address, arguments)

    def start(self, runtime, state: CueState) -> None:
        cue = state.cue
        fade_type = int(cue.params.get("fade_type", 0))
        state.network_next = 0.0
        if fade_type == 0:
            self._send(runtime, cue, None)
        else:
            self._send(runtime, cue, self._values(runtime, state, 0.0))
            state.network_next = 1.0 / max(1, int(cue.params.get("fps", 30)))

    def _values(self, runtime: Runtime, state: CueState, position: float) -> list:
        cue = state.cue
        params = cue.params
        fade_type = int(params.get("fade_type", 0))
        curve = params.get("curve")
        shaped = curves.interpolate(0.0, 1.0, position, curve)
        if fade_type == 1:
            start = float(params.get("fade_from", 0.0))
            end = float(params.get("fade_to", 1.0))
            return [start + (end - start) * shaped]
        path = params.get("path", [])
        if len(path) < 2:
            return [0.0, 0.0]
        lengths = []
        total = 0.0
        for index in range(len(path) - 1):
            distance = ((path[index + 1][0] - path[index][0]) ** 2 + (path[index + 1][1] - path[index][1]) ** 2) ** 0.5
            lengths.append(distance)
            total = total + distance
        target = shaped * total
        for index, distance in enumerate(lengths):
            if target <= distance or index == len(lengths) - 1:
                fraction = 0.0 if distance == 0 else min(1.0, target / distance)
                return [path[index][0] + (path[index + 1][0] - path[index][0]) * fraction,
                        path[index][1] + (path[index + 1][1] - path[index][1]) * fraction]
            target = target - distance
        return list(path[-1])

    def update(self, runtime, state: CueState) -> None:
        cue = state.cue
        if int(cue.params.get("fade_type", 0)) == 0 or state.action_duration <= 0:
            return
        while state.action_elapsed >= state.network_next and state.network_next < state.action_duration:
            position = min(1.0, state.network_next / state.action_duration)
            self._send(runtime, cue, self._values(runtime, state, position))
            state.network_next = state.network_next + 1.0 / max(1, int(cue.params.get("fps", 30)))

    def stop(self, runtime, state: CueState, hard: bool) -> None:
        cue = state.cue
        if int(cue.params.get("fade_type", 0)) != 0 and state.action_duration > 0 and hard == False \
                and state.action_elapsed >= state.action_duration - 1e-6:
            self._send(runtime, cue, self._values(runtime, state, 1.0))


class MidiHandler(ActionHandler):
    def __init__(self, hub: OutputHub):
        self.hub = hub

    def build(self, cue: Cue, byte2_override: int | None = None) -> tuple[bytes, str]:
        params = cue.params
        message_type = int(params.get("message_type", 1))
        if message_type == 1:
            status = int(params["status"])
            byte2 = int(params["byte2"]) if byte2_override is None else byte2_override
            if status == 6:
                value = int(params["byte1"]) | (byte2 << 7)
                return pitch_bend_message(int(params["channel"]), value), "midiOutput"
            return voice_message(status, int(params["channel"]), int(params["byte1"]), byte2), "midiOutput"
        if message_type == 2:
            timecode = tuple(params.get("timecode", [0, 0, 0, 0, 0]))
            return msc_message(int(params["command_format"]), int(params["command"]), int(params["device_id"]),
                               str(params["q_number"]), str(params["q_list"]), str(params["q_path"]),
                               int(params["control_number"]), int(params["control_value"]),
                               timecode if int(params["command"]) == MSC_COMMANDS["SET"] else None,
                               int(params.get("timecode_format", 1))), "mscOutput"
        return sysex_from_text(str(params["raw_string"])), "sysexOutput"

    def start(self, runtime, state: CueState) -> None:
        cue = state.cue
        data, override = self.build(cue)
        self.hub.send_midi(int(cue.params["midi_patch"]), data, override)
        state.midi_next = 0.0
        state.midi_last_value = int(cue.params["byte2"])

    def update(self, runtime, state: CueState) -> None:
        cue = state.cue
        params = cue.params
        end_value = params.get("end_value")
        if end_value is None or int(params.get("message_type", 1)) != 1 or state.action_duration <= 0:
            return
        position = min(1.0, state.action_elapsed / state.action_duration)
        begin = int(params["byte2"])
        value = int(round(curves.interpolate(begin, int(end_value), position, params.get("curve"))))
        if value != state.midi_last_value:
            data, override = self.build(cue, value)
            self.hub.send_midi(int(params["midi_patch"]), data, override)
            state.midi_last_value = value


    def stop(self, runtime, state: CueState, hard: bool) -> None:
        params = state.cue.params
        end_value = params.get("end_value")
        if end_value is None or hard == True or int(params.get("message_type", 1)) != 1:
            return
        if state.action_duration > 0 and state.action_elapsed >= state.action_duration - 1e-6:
            if state.midi_last_value != int(end_value):
                data, override = self.build(state.cue, int(end_value))
                self.hub.send_midi(int(params["midi_patch"]), data, override)
                state.midi_last_value = int(end_value)


class MidiFileHandler(ActionHandler):
    cache: dict = {}

    def __init__(self, hub: OutputHub):
        self.hub = hub

    def _events(self, cue: Cue):
        path = cue.params.get("file_target", "")
        if path not in self.cache:
            with open(path, "rb") as handle:
                self.cache[path] = parse_midi_file(handle.read())
        return self.cache[path]

    def start(self, runtime, state: CueState) -> None:
        events, duration = self._events(state.cue)
        state.midi_events = events
        state.midi_index = 0
        state.midi_notes = set()
        self.update(runtime, state)

    def update(self, runtime, state: CueState) -> None:
        rate = max(0.01, float(state.cue.params.get("playback_rate", 1.0)))
        now = state.action_elapsed * rate
        patch = int(state.cue.params.get("midi_patch", 1))
        while state.midi_index < len(state.midi_events) and state.midi_events[state.midi_index][0] <= now + 1e-9:
            data = state.midi_events[state.midi_index][1]
            kind = data[0] & 0xF0
            if kind == 0x90 and len(data) == 3 and data[2] > 0:
                state.midi_notes.add((data[0] & 0x0F, data[1]))
            elif kind in (0x80, 0x90) and len(data) == 3:
                state.midi_notes.discard((data[0] & 0x0F, data[1]))
            self.hub.send_midi(patch, bytes(data), "sysexOutput" if data[0] == 0xF0 else "midiOutput")
            state.midi_index = state.midi_index + 1

    def stop(self, runtime, state: CueState, hard: bool) -> None:
        patch = int(state.cue.params.get("midi_patch", 1))
        for channel, note in sorted(getattr(state, "midi_notes", set())):
            self.hub.send_midi(patch, bytes([0x80 | channel, note, 0]))
        state.midi_notes = set()


class TimecodeHandler(ActionHandler):
    def __init__(self, hub: OutputHub):
        self.hub = hub

    def start(self, runtime, state: CueState) -> None:
        params = state.cue.params
        state.tc_origin = parse_timecode_text(str(params.get("start_time", "00:00:00:00")))
        state.tc_format = int(params.get("format", 1))
        state.tc_start_seconds = timecode_to_seconds(*state.tc_origin, state.tc_format)
        state.tc_quarter_index = 0
        state.tc_ltc_state = None
        state.tc_last_frame = None
        if params.get("kind", "mtc") == "mtc":
            self.hub.send_midi(int(params.get("midi_patch", 1)), mtc_full_frame(state.tc_origin, state.tc_format),
                               "timecodeOutput")
        self.update(runtime, state)

    def update(self, runtime, state: CueState) -> None:
        params = state.cue.params
        real = TIMECODE_FORMATS[state.tc_format][1]
        position = state.tc_start_seconds + state.action_elapsed
        if params.get("kind", "mtc") == "mtc":
            quarter_period = 1.0 / (real * 4.0)
            total_quarters = int(state.action_elapsed / quarter_period + 1e-9)
            while state.tc_quarter_index <= total_quarters:
                frame_time = state.tc_start_seconds + (state.tc_quarter_index // 8) * 2 / real
                timecode = seconds_to_timecode(frame_time, state.tc_format)
                data = mtc_quarter_frames(timecode, state.tc_format)[state.tc_quarter_index % 8]
                self.hub.send_midi(int(params.get("midi_patch", 1)), data, "timecodeOutput")
                state.tc_quarter_index = state.tc_quarter_index + 1
        else:
            timecode = seconds_to_timecode(position, state.tc_format)
            if timecode != state.tc_last_frame:
                state.tc_last_frame = timecode
                self.hub.ltc_frames.append((int(params.get("audio_output_patch", 1)), timecode, state.tc_format))
