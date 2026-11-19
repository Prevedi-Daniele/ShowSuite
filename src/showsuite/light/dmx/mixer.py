"""Mixer: unisce più sorgenti per universo. Per ora LTP per priorità.

Ogni sorgente ha una priorità; per ogni canale vince il valore scritto
dalla sorgente con priorità più alta tra quelle che lo hanno impostato.
"""
from __future__ import annotations

from .universe import DMX_CHANNELS


class Layer:
    def __init__(self, priority: int):
        self.priority = priority
        self.values: dict[int, dict[int, int]] = {}  # universe -> {canale: valore}

    def set(self, universe: int, channel: int, value: int) -> None:
        if not 1 <= channel <= DMX_CHANNELS:
            raise ValueError("canale fuori range")
        self.values.setdefault(universe, {})[channel] = max(0, min(255, int(value)))

    def release(self, universe: int, channel: int) -> None:
        self.values.get(universe, {}).pop(channel, None)


class Mixer:
    def __init__(self):
        self.layers: list[Layer] = []

    def add_layer(self, priority: int) -> Layer:
        layer = Layer(priority)
        self.layers.append(layer)
        self.layers.sort(key=lambda l: l.priority)
        return layer

    def render(self, universe: int) -> bytes:
        out = bytearray(DMX_CHANNELS)
        for layer in self.layers:  # dal meno al più prioritario: l'ultimo vince
            for ch, v in layer.values.get(universe, {}).items():
                out[ch - 1] = v
        return bytes(out)

    def universes(self) -> set[int]:
        return {u for l in self.layers for u in l.values}
