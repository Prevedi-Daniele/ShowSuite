"""Effetti colore: sequenza di colori (swatch) oppure curve Hue/Saturation/Brightness."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .properties import hsb_to_rgb


def _lerp(a, b, k):
    return a + (b - a) * k


def curve_value(points: list[tuple[float, float]], x: float) -> float:
    """Interpolazione coseno fra punti (x 0-1, y 0-1) ordinati; la curva è ciclica sul periodo 1."""
    pts = sorted(points)
    if not pts:
        return 0.0
    if len(pts) == 1:
        return pts[0][1]
    x %= 1.0
    ext = [(pts[-1][0] - 1.0, pts[-1][1])] + pts + [(pts[0][0] + 1.0, pts[0][1])]
    for (x0, y0), (x1, y1) in zip(ext, ext[1:]):
        if x0 <= x <= x1:
            k = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            return _lerp(y0, y1, 0.5 - 0.5 * math.cos(math.pi * k))
    return pts[0][1]


def hue_wheel() -> list[tuple[float, float]]:
    """Curva Hue che attraversa l'intero spettro (arcobaleno)."""
    return [(0.0, 0.0), (1 / 3, 1 / 3), (2 / 3, 2 / 3), (1.0, 1.0)]


@dataclass
class ColorEffect:
    mode: str = "swatches"                 # "swatches" | "curves"
    swatches: list[tuple[int, int, int]] = field(default_factory=lambda: [(255, 0, 0), (0, 0, 255)])
    hue: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 0.0), (0.5, 0.5)])
    saturation: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 1.0)])
    brightness: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 1.0)])
    duration: float = 5.0
    time_offset: float = 0.04              # sfasamento distribuito sui fixture (0-1)
    crossfade: bool = True                 # swatch: sfuma fra i colori invece di scattare

    def color(self, t: float, index: int = 0, count: int = 1) -> tuple[int, int, int]:
        p = t / self.duration + self.time_offset * index / max(1, count)
        if self.mode == "curves":
            return hsb_to_rgb(curve_value(self.hue, p) * 360, curve_value(self.saturation, p),
                              curve_value(self.brightness, p))
        if not self.swatches:
            return (0, 0, 0)
        n = len(self.swatches); x = (p % 1.0) * n; i = int(x); k = x - i
        a, b = self.swatches[i % n], self.swatches[(i + 1) % n]
        if not self.crossfade:
            return a
        return tuple(round(_lerp(a[c], b[c], k)) for c in range(3))

    def evaluate(self, fixtures: list[str], t: float) -> dict[str, tuple[int, int, int]]:
        n = len(fixtures)
        return {f: self.color(t, i, n) for i, f in enumerate(fixtures)}

    def apply(self, engine, fixtures: list[str], t: float) -> None:
        from . import properties as P
        for f, rgb in self.evaluate(fixtures, t).items():
            P.set_color(engine, [f], rgb)
