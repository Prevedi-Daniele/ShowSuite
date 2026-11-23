"""Fanning (come in Lightkey): distribuisce un valore da `start` a `end` sui fixture, nell'ordine dato."""
from __future__ import annotations

from .properties import hsb_to_rgb, set_color, set_dimmer, set_position, set_simple

FAN_PROPS = ("dimmer", "hue", "pan", "tilt", "zoom", "focus", "iris", "frost")
CURVES = {"linear": lambda t: t, "ease": lambda t: t * t * (3 - 2 * t),
          "in": lambda t: t * t, "out": lambda t: 1 - (1 - t) ** 2}


def fan_values(n: int, start: float, end: float, curve: str = "linear", symmetric: bool = False) -> list[float]:
    f = CURVES[curve]
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.5
        if symmetric:
            t = 1 - abs(2 * t - 1)      # 0 ai bordi → 1 al centro
        out.append(start + (end - start) * f(t))
    return out


def fan(engine, fixtures: list[str], prop: str, start: float, end: float,
        curve: str = "linear", symmetric: bool = False) -> int:
    """start/end 0-1 (per hue: 0-1 = 0-360°). Ritorna quanti fixture sono stati toccati."""
    if prop not in FAN_PROPS:
        raise ValueError(f"proprietà non fan-abile: {prop}")
    vals = fan_values(len(fixtures), start, end, curve, symmetric)
    for name, v in zip(fixtures, vals):
        if prop == "dimmer":
            set_dimmer(engine, [name], round(v * 255))
        elif prop == "hue":
            set_color(engine, [name], hsb_to_rgb(v * 360 % 360 if v < 1 else 359.9, 1.0, 1.0))
        elif prop == "pan":
            set_position(engine, [name], pan=v)
        elif prop == "tilt":
            set_position(engine, [name], tilt=v)
        else:
            set_simple(engine, [name], prop, v)
    return len(fixtures)
