"""Effetti di posizione: figure percorse da pan/tilt (valori normalizzati -1..1, 0 = centro)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


def _tri(p):            # triangolo 0..1..0
    p %= 1.0
    return 1 - abs(2 * p - 1)


def _poly(points):
    """Percorso lineare chiuso fra punti (x, y)."""
    def f(p):
        p %= 1.0
        n = len(points); t = p * n; i = int(t); k = t - i
        (x0, y0), (x1, y1) = points[i % n], points[(i + 1) % n]
        return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    return f


PATTERNS = {
    "Triangle Small": _poly([(0, -0.6), (0.4, 0.3), (-0.4, 0.3)]),
    "Triangle Wide": _poly([(0, -0.9), (0.9, 0.6), (-0.9, 0.6)]),
    "Wedge Straight": _poly([(-0.8, 0.5), (0, -0.2), (0.8, 0.5), (0, -0.2)]),
    "Wedge Curved": lambda p: (math.sin(2 * math.pi * p) * 0.8, 0.5 - 0.7 * abs(math.sin(math.pi * p))),
    "Tilt Track 1": lambda p: (0.0, math.sin(2 * math.pi * p) * 0.6),
    "Tilt Track 2": lambda p: (0.0, math.sin(2 * math.pi * p) * 0.9),
    "Pan Track": lambda p: (math.sin(2 * math.pi * p) * 0.9, 0.0),
    "Zigzag 2": lambda p: ((_tri(p * 2) * 2 - 1) * 0.8, (_tri(p) * 2 - 1) * 0.5),
    "Zigzag 5": lambda p: ((_tri(p * 5) * 2 - 1) * 0.8, (_tri(p) * 2 - 1) * 0.5),
    "Bow Tie": lambda p: (math.sin(2 * math.pi * p) * 0.8, math.sin(4 * math.pi * p) * 0.4),
    "Flower": lambda p: tuple(0.9 * math.cos(6 * math.pi * p) * v for v in (math.cos(2 * math.pi * p), math.sin(2 * math.pi * p))),
    "Half Flower 3": lambda p: tuple(0.9 * abs(math.cos(3 * math.pi * p)) * v for v in (math.cos(2 * math.pi * p), math.sin(2 * math.pi * p) * 0.6 - 0.2)),
    "Half Flower 5": lambda p: tuple(0.9 * abs(math.cos(5 * math.pi * p)) * v for v in (math.cos(2 * math.pi * p), math.sin(2 * math.pi * p) * 0.6 - 0.2)),
    "Random Dots": None,    # gestito a parte: punti casuali stabili
    "Path": None,           # percorso disegnato dall'utente (campo `path`)
}


def _catmull(points, p, smooth=True):
    """Punto a fase p (0-1) su un percorso chiuso fra `points`: spline Catmull-Rom o spezzata."""
    n = len(points); t = (p % 1.0) * n; i = int(t); k = t - i
    p0, p1, p2, p3 = (points[(i + j) % n] for j in (-1, 0, 1, 2))
    if not smooth:
        return (p1[0] + (p2[0] - p1[0]) * k, p1[1] + (p2[1] - p1[1]) * k)
    def c(a, b, c_, d):
        return 0.5 * (2 * b + (-a + c_) * k + (2 * a - 5 * b + 4 * c_ - d) * k * k + (-a + 3 * b - 3 * c_ + d) * k ** 3)
    return c(p0[0], p1[0], p2[0], p3[0]), c(p0[1], p1[1], p2[1], p3[1])


@dataclass
class PositionEffect:
    pattern: str = "Flower"
    duration: float = 5.0         # secondi per ciclo
    time_offset: float = 1.0      # 0-1: sfasamento distribuito fra i fixture (100% = fase completa)
    pan_offset: float = 0.0       # gradi aggiunti progressivamente ai fixture
    tilt_offset: float = 0.0
    size: float = 1.0             # 0-1 scala della figura
    pan_range: float = 540.0      # gradi totali (pan/tilt del profilo: 540/270 tipico)
    tilt_range: float = 270.0
    path: list = field(default_factory=list)   # punti (x, y) -1..1 del movement path (pattern "Path")
    smooth: bool = True                        # path: spline (True) o spezzata (False)
    reverse: bool = False                      # direzione inversa

    def point(self, t: float, index: int = 0, count: int = 1) -> tuple[float, float]:
        """Posizione (pan, tilt) in -1..1 al tempo t (secondi) per il fixture `index`."""
        if self.pattern not in PATTERNS:
            raise ValueError(f"figura sconosciuta: {self.pattern}")
        p = t / self.duration + self.time_offset * (index / max(1, count))
        if self.reverse:
            p = -p
        if self.pattern == "Path":
            pts = [tuple(q) for q in self.path]
            if len(pts) < 2:
                x, y = pts[0] if pts else (0.0, 0.0)
            else:
                x, y = _catmull(pts, p, self.smooth)
        elif self.pattern == "Random Dots":
            r = random.Random(int(p * 8) * 7919 + index)
            x, y = r.uniform(-0.8, 0.8), r.uniform(-0.8, 0.8)
        else:
            x, y = PATTERNS[self.pattern](p)
        x = x * self.size + self.pan_offset * index / (self.pan_range / 2)
        y = y * self.size + self.tilt_offset * index / (self.tilt_range / 2)
        return max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y))

    def evaluate(self, fixtures: list[str], t: float) -> dict[str, tuple[float, float]]:
        n = len(fixtures)
        return {f: self.point(t, i, n) for i, f in enumerate(fixtures)}

    def degrees(self, x: float, y: float) -> tuple[float, float]:
        return x * self.pan_range / 2, y * self.tilt_range / 2

    def apply(self, engine, fixtures: list[str], t: float) -> None:
        """Scrive pan/tilt nel programmer (0.5 = centro)."""
        from . import properties as P
        for f, (x, y) in self.evaluate(fixtures, t).items():
            P.set_position(engine, [f], pan=0.5 + x / 2, tilt=0.5 + y / 2)


POSITION_LIBRARY: dict[str, PositionEffect] = {
    "Slow Circle": PositionEffect("Flower", 12.0, 0.5, size=0.5),
    "Fan Sweep": PositionEffect("Pan Track", 6.0, 0.0, size=0.8),
    "Nod": PositionEffect("Tilt Track 1", 3.0, 0.0, size=0.7),
    "Figure Eight": PositionEffect("Bow Tie", 8.0, 0.5),
    "Triangle Dance": PositionEffect("Triangle Wide", 6.0, 1.0),
    "Chaos": PositionEffect("Random Dots", 4.0, 1.0, size=0.9),
}


def position_template(name: str) -> PositionEffect:
    import copy
    return copy.deepcopy(POSITION_LIBRARY[name])
