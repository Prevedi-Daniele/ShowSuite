"""Integrazione Cue <-> Light: il Light cue pilota la sezione Light (in locale o via OSC).

Linguaggio comandi (una riga per comando, nel parametro `commands` del Light cue):
    cue <nome|numero>            avvia un cue Live di Light          (release <nome> lo rilascia)
    <fixture>.<canale> <0-100>   imposta un canale (fade sulla durata del cue)
    <fixture> <0-100>            come sopra sul canale Dimmer/Intensity
    master|bpm|blackout|freeze|blind <0-100>
    osc /indirizzo [argomenti]   messaggio OSC grezzo verso Light (solo bridge locale e remoto)
Non è la sintassi testuale di QLab (che dipende dal Light dashboard di macOS): è un linguaggio equivalente."""
from __future__ import annotations

import shlex

from . import curves
from .engine import ActionHandler, CueState, Runtime
from .model import TYPE_LIGHT
from .osc import parse_plain_text

PLAIN_ACTIONS = ("master", "bpm", "blackout", "freeze", "blind")
DIMMER_NAMES = ("dimmer", "intensity")


def parse_command(line: str) -> dict:
    tokens = shlex.split(line.strip())
    if len(tokens) == 0:
        raise ValueError("comando vuoto")
    head = tokens[0].lower()
    if head in ("cue", "go", "release") and len(tokens) >= 2:
        return {"kind": "cue", "name": " ".join(tokens[1:]), "on": head != "release"}
    if head in PLAIN_ACTIONS and len(tokens) == 2:
        return {"kind": "plain", "action": head, "value": float(tokens[1]) / 100.0}
    if head == "osc" and len(tokens) >= 2:
        address, arguments = parse_plain_text(" ".join(tokens[1:]))
        return {"kind": "osc", "address": address, "arguments": arguments}
    if len(tokens) >= 2:
        target = " ".join(tokens[:-1])
        value = float(tokens[-1].rstrip("%"))
        fixture, dot, channel = target.rpartition(".")
        if dot == "":
            fixture, channel = target, ""
        return {"kind": "fixture", "fixture": fixture, "channel": channel, "value": value / 100.0}
    raise ValueError("comando non valido: " + line)


class LocalLightBridge:
    """Pilota direttamente un `ActionRunner` della sezione Light nello stesso processo."""

    def __init__(self, runner):
        self.runner = runner

    def _channel_name(self, fixture: str, channel: str) -> str:
        fx = self.runner.engine.project.patch.find(fixture)
        if channel == "":
            for candidate in fx.profile.channels:
                if candidate.name.lower() in DIMMER_NAMES:
                    return candidate.name
            return fx.profile.channels[0].name
        for candidate in fx.profile.channels:
            if candidate.name.lower() == channel.lower():
                return candidate.name
        raise ValueError("canale sconosciuto: " + channel)

    def current_value(self, command: dict) -> float:
        name = self._channel_name(command["fixture"], command["channel"])
        return self.runner.engine.get_value(command["fixture"], name) / 255.0

    def apply(self, command: dict, value: float | None = None) -> None:
        kind = command["kind"]
        if kind == "cue":
            self.runner.run("cue", {"cue": command["name"]}, 1.0 if command["on"] else 0.0)
        elif kind == "plain":
            self.runner.run(command["action"], {}, command["value"])
        elif kind == "fixture":
            name = self._channel_name(command["fixture"], command["channel"])
            self.runner.run("fixture", {"fixture": command["fixture"], "channel": name},
                            command["value"] if value is None else value)
        elif kind == "osc":
            from ..light.control.osc import dispatch
            dispatch(self.runner, command["address"], command["arguments"])

    def dashboard(self, path: list, arguments: list):
        if path[:1] == ["clear"]:
            self.runner.engine.clear_programmer()
            return "ok"
        if path[:1] == ["setLight"]:
            target = path[1] if len(path) > 1 else str(arguments[0])
            value = float(arguments[-1] if len(path) > 1 else arguments[1])
            fixture, dot, channel = target.rpartition(".")
            if dot == "":
                fixture, channel = target, ""
            self.apply({"kind": "fixture", "fixture": fixture, "channel": channel, "value": value / 100.0})
            return "ok"
        raise ValueError("comando dashboard non supportato: " + "/".join(path))


class RemoteLightBridge:
    """Invia a Light i comandi come messaggi OSC (stile Lightkey) tramite un patch di rete dei Cue."""

    def __init__(self, hub, network_patch: int):
        self.hub = hub
        self.network_patch = network_patch
        self.known: dict = {}

    def current_value(self, command: dict) -> float:
        return self.known.get((command["fixture"], command["channel"]), 0.0)

    def apply(self, command: dict, value: float | None = None) -> None:
        from .osc import encode_message
        kind = command["kind"]
        if kind == "cue":
            address, arguments = "/cue/" + command["name"], [1.0 if command["on"] else 0.0]
        elif kind == "plain":
            address, arguments = "/" + command["action"], [command["value"]]
        elif kind == "fixture":
            level = command["value"] if value is None else value
            self.known[(command["fixture"], command["channel"])] = level
            channel = command["channel"] or "Dimmer"
            address, arguments = "/fixture/%s/%s" % (command["fixture"], channel), [level]
        else:
            address, arguments = command["address"], command["arguments"]
        self.hub.send_network(self.network_patch, "osc", encode_message(address, arguments), address, arguments)

    def dashboard(self, path: list, arguments: list):
        raise ValueError("dashboard remoto non disponibile")


class LightHandler(ActionHandler):
    def __init__(self, bridge):
        self.bridge = bridge

    def start(self, runtime: Runtime, state: CueState) -> None:
        commands = []
        for line in state.cue.params.get("commands", []):
            commands.append(parse_command(line))
        state.light_commands = commands
        state.light_begin = {}
        for index, command in enumerate(commands):
            if command["kind"] == "fixture" and state.action_duration > 0:
                state.light_begin[index] = self.bridge.current_value(command)
            elif command["kind"] != "fixture" or state.action_duration <= 0:
                self.bridge.apply(command)
        if state.action_duration <= 0:
            return
        self.update(runtime, state)

    def update(self, runtime: Runtime, state: CueState) -> None:
        if state.action_duration <= 0:
            return
        position = min(1.0, state.action_elapsed / state.action_duration)
        curve = state.cue.params.get("curve")
        for index, begin in state.light_begin.items():
            command = state.light_commands[index]
            value = curves.interpolate(begin, command["value"], position, curve)
            self.bridge.apply(command, value)

    def stop(self, runtime: Runtime, state: CueState, hard: bool) -> None:
        if hard == False and state.action_duration > 0 and state.action_elapsed >= state.action_duration - 1e-6:
            for index in getattr(state, "light_begin", {}):
                self.bridge.apply(state.light_commands[index])


def install_light_bridge(runtime: Runtime, bridge) -> None:
    runtime.light_bridge = bridge
    runtime.register_handler(TYPE_LIGHT, LightHandler(bridge))
