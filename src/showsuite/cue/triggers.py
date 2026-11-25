"""Trigger dei cue: hotkey, MIDI, MIDI Show Control, wall clock, timecode (MTC/LTC già decodificati).

Il gestore non apre porte: riceve eventi (`midi_in`, `key_event`, `wall_clock_tick`, `timecode_input`) da chi li produce."""
from __future__ import annotations

import datetime

from .engine import ORIGIN_TRIGGER, Runtime
from .model import TYPE_CART, TYPE_LIST, Cue
from .protocols import (MSC_ACCEPTED_FORMATS, MSC_COMMANDS, MtcDecoder, parse_msc, parse_timecode_text,
                        timecode_to_seconds)

VOICE_NAMES = {"note_off": 0x80, "note_on": 0x90, "key_pressure": 0xA0, "control_change": 0xB0,
               "program_change": 0xC0, "channel_pressure": 0xD0, "pitch_bend": 0xE0}


def match_byte(pattern, value: int) -> bool:
    """Regole: 'any', numero, '>N', 'N-M'."""
    text = str(pattern).strip().lower()
    if text in ("any", "*", ""):
        return True
    if text.startswith(">"):
        return value > int(text[1:])
    if text.startswith("<"):
        return value < int(text[1:])
    if "-" in text[1:]:
        low, high = text.split("-", 1)
        return int(low) <= value <= int(high)
    return value == int(text)


def match_midi_trigger(trigger: dict, data: bytes) -> bool:
    if len(data) < 2 or data[0] >= 0xF0:
        return False
    status = VOICE_NAMES.get(trigger.get("status", "note_on"), 0x90)
    channel = int(trigger.get("channel", 0))
    if (data[0] & 0xF0) != status:
        return False
    if channel > 0 and (data[0] & 0x0F) != channel - 1:
        return False
    byte2 = data[2] if len(data) > 2 else 0
    # Note On con velocity 0 è un Note Off: non scatta
    if status == 0x90 and byte2 == 0 and len(data) > 2:
        return False
    return match_byte(trigger.get("byte1", "any"), data[1]) and match_byte(trigger.get("byte2", "any"), byte2)


class TriggerManager:
    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        self.last_wall_second: dict[str, str] = {}
        self.timecode_state: dict[str, dict] = {}
        self.held_keys: dict[str, Cue] = {}
        self.mtc = MtcDecoder()

    # --- util ---
    def _cues_with(self, key: str) -> list[Cue]:
        return [cue for cue in self.runtime.workspace.all_cues() if cue.triggers.get(key)]

    def _fire(self, cue: Cue) -> None:
        if self.runtime.workspace.settings.get("show_mode", False) == False or True:
            self.runtime.start_cue(cue, origin=ORIGIN_TRIGGER)

    # --- hotkey ---
    def key_event(self, sequence: str, pressed: bool) -> list[Cue]:
        fired = []
        with self.runtime.lock:
            if pressed == True:
                for cue in self._cues_with("hotkey"):
                    if cue.triggers["hotkey"] == sequence:
                        self.held_keys[sequence] = cue
                        self._fire(cue)
                        fired.append(cue)
            else:
                cue = self.held_keys.pop(sequence, None)
                if cue is not None:
                    self.runtime.release_trigger(cue)
        return fired

    # --- MIDI e MSC ---
    def midi_in(self, data: bytes) -> list[Cue]:
        fired = []
        settings = self.runtime.workspace.settings
        with self.runtime.lock:
            if data[:1] == b"\xF0":
                if settings["overrides"].get("mscInput", True) == False:
                    return fired
                if settings.get("use_msc", False) == True:
                    self._handle_msc(data)
                return fired
            if settings["overrides"].get("midiInput", True) == False:
                return fired
            for cue in self._cues_with("midi"):
                trigger = cue.triggers["midi"]
                if match_midi_trigger(trigger, data):
                    if (data[0] & 0xF0) == 0x80 or ((data[0] & 0xF0) == 0x90 and len(data) > 2 and data[2] == 0):
                        continue
                    self._fire(cue)
                    fired.append(cue)
        return fired

    def midi_release(self, data: bytes) -> None:
        """Note Off / Note On vel 0: vale come rilascio per `secondTriggerOnRelease`."""
        with self.runtime.lock:
            for cue in self._cues_with("midi"):
                trigger = cue.triggers["midi"]
                if (data[0] & 0xF0) in (0x80, 0x90) and trigger.get("status", "note_on") in ("note_on", "note_off"):
                    if match_byte(trigger.get("byte1", "any"), data[1]):
                        self.runtime.release_trigger(cue)

    def _handle_msc(self, data: bytes) -> None:
        message = parse_msc(data)
        settings = self.runtime.workspace.settings
        runtime = self.runtime
        if message is None or message["command_format"] not in MSC_ACCEPTED_FORMATS:
            return
        device = int(settings.get("msc_device_id", 0))
        if message["device_id"] not in (device, 127):
            return
        command = message["command"]
        number = message["q_number"]
        target = runtime.workspace.find_by_number(number) if number != "" else None
        if number != "" and target is None and command in (1, 2, 3, 5, 10):
            return
        if command == MSC_COMMANDS["GO"]:
            if target is None:
                runtime.go(origin=ORIGIN_TRIGGER)
            else:
                runtime.start_cue(target, origin=ORIGIN_TRIGGER)
        elif command == MSC_COMMANDS["STOP"]:
            if target is None:
                runtime.pause_all()
            else:
                runtime.pause_cue(target)
        elif command == MSC_COMMANDS["RESUME"]:
            if target is None:
                runtime.resume_all()
            else:
                runtime.resume_cue(target)
        elif command == MSC_COMMANDS["LOAD"]:
            runtime.load_cue(target if target is not None else runtime.playhead())
        elif command == MSC_COMMANDS["ALL_OFF"]:
            runtime.panic_all()
        elif command == MSC_COMMANDS["STANDBY_PLUS"]:
            runtime.move_playhead_next()
        elif command == MSC_COMMANDS["STANDBY_MINUS"]:
            runtime.move_playhead_previous()
        elif command == MSC_COMMANDS["SEQUENCE_PLUS"]:
            runtime.move_playhead_next_sequence()
        elif command == MSC_COMMANDS["SEQUENCE_MINUS"]:
            runtime.move_playhead_previous_sequence()
        elif command == MSC_COMMANDS["RESET"]:
            if target is None:
                runtime.reset_workspace()
            else:
                runtime.reset_cue(target)

    # --- wall clock ---
    def wall_clock_tick(self, now: datetime.datetime | None = None) -> list[Cue]:
        now = now if now is not None else datetime.datetime.now()
        stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        text = now.strftime("%H:%M:%S")
        fired = []
        with self.runtime.lock:
            for cue in self._cues_with("wall_clock"):
                trigger = cue.triggers["wall_clock"]
                wanted = trigger.get("time", "")
                if len(wanted.split(":")) == 2:
                    wanted = wanted + ":00"
                days = trigger.get("days", [])
                if wanted != text or (len(days) > 0 and now.weekday() not in days):
                    continue
                if self.last_wall_second.get(cue.unique_id) == stamp:
                    continue
                self.last_wall_second[cue.unique_id] = stamp
                self._fire(cue)
                fired.append(cue)
        return fired

    # --- timecode ---
    def timecode_input(self, container: Cue, seconds: float, now: float | None = None) -> list[Cue]:
        """Posizione timecode (secondi) di una lista/cart con sync attivo."""
        runtime = self.runtime
        now = now if now is not None else runtime.clock.now()
        params = container.params
        if params.get("timecode_sync", False) == False:
            return []
        fired = []
        with runtime.lock:
            state = self.timecode_state.setdefault(container.unique_id, {"last": None, "running": False,
                                                                       "last_arrival": now, "paused": False})
            previous = state["last"]
            state["last_arrival"] = now
            if state["paused"] == True:
                runtime.resume_cue(container)
                state["paused"] = False
            fired_range = None
            if previous is None or state["running"] == False:
                state["running"] = True
                low, high = self._start_range(params, seconds)
                fired_range = (low, high, True)
            elif seconds > previous and seconds - previous < 1.0:
                fired_range = (previous, seconds, False)
            if fired_range is not None:
                fired = self._fire_timecode(container, fired_range[0], fired_range[1], include_low=fired_range[2])
            state["last"] = seconds
        return fired

    @staticmethod
    def _start_range(params: dict, seconds: float) -> tuple[float, float]:
        behavior = int(params.get("timecode_start_behavior", 0))
        if behavior == 0:
            return seconds, seconds
        if behavior == 1:
            return max(0.0, seconds - 60.0), seconds
        if behavior == 2:
            return max(0.0, seconds - 3600.0), seconds
        if behavior == 3:
            return max(0.0, seconds - float(params.get("timecode_lookback_time", 5.0))), seconds
        return 0.0, seconds

    def _fire_timecode(self, container: Cue, low: float, high: float, include_low: bool = True) -> list[Cue]:
        format_index = int(container.params.get("timecode_format", 1))
        fired = []
        for cue in container.walk():
            trigger = cue.triggers.get("timecode")
            if not trigger:
                continue
            hours, minutes, seconds, frames = parse_timecode_text(str(trigger.get("time", "0:0:0:0")))
            moment = timecode_to_seconds(hours, minutes, seconds, frames, format_index)
            above = moment >= low - 1e-9 if include_low == True else moment > low + 1e-9
            if above == True and moment <= high + 1e-9:
                self._fire(cue)
                fired.append(cue)
        return fired

    def timecode_check_signal(self, container: Cue, now: float | None = None) -> None:
        """Da chiamare periodicamente: gestisce freewheel e stop behavior quando il segnale sparisce."""
        runtime = self.runtime
        now = now if now is not None else runtime.clock.now()
        state = self.timecode_state.get(container.unique_id)
        if state is None or state["running"] == False:
            return
        freewheel = float(container.params.get("timecode_freewheel_time", 0.0))
        if now - state["last_arrival"] <= freewheel:
            return
        state["running"] = False
        state["last"] = None
        behavior = int(container.params.get("timecode_stop_behavior", 0))
        if behavior == 1:
            runtime.pause_cue(container)
            state["paused"] = True
        elif behavior == 2:
            runtime.stop_cue(container)
