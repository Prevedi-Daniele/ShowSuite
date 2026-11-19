"""Effetti: onde applicate a un canale di più fixture, con fanning di fase."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

WAVES = {
    "sine": lambda p: 0.5 - 0.5 * math.cos(2 * math.pi * p),
    "triangle": lambda p: 1 - abs(2 * (p % 1.0) - 1),
    "saw": lambda p: p % 1.0,
    "ramp_down": lambda p: 1 - (p % 1.0),
    "square": lambda p: 1.0 if (p % 1.0) < 0.5 else 0.0,
}


@dataclass
class Effect:
    channel: str                  # es. "Dimmer", "Red", "Pan"
    wave: str = "sine"
    beats_per_cycle: float = 1.0  # durata di un ciclo in battute
    minimum: int = 0
    maximum: int = 255
    fan: float = 0.0              # 0-1: sfasamento totale distribuito sui fixture
    reverse: bool = False

    def value(self, beats: float, index: int = 0, count: int = 1) -> int:
        if self.wave not in WAVES and self.wave != "random":
            raise ValueError(f"onda sconosciuta: {self.wave}")
        offset = self.fan * (index / count if count else 0)
        phase = beats / self.beats_per_cycle + (offset if not self.reverse else -offset)
        if self.wave == "random":
            x = random.Random(int(math.floor(phase)) * 7919 + index).random()
        else:
            x = WAVES[self.wave](phase)
        return round(self.minimum + (self.maximum - self.minimum) * x)

    def evaluate(self, fixtures: list[str], beats: float) -> dict[str, int]:
        n = len(fixtures)
        return {f: self.value(beats, i, n) for i, f in enumerate(fixtures)}
