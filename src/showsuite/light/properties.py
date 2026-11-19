"""Proprietà fixture (Design view): colore HSB, dimmer assoluto/relativo, stato override.

Una proprietà "definita" (override) sta nel programmer e vince su preset, sequenze e cue.
"""
from __future__ import annotations

import colorsys

from .engine import LightEngine

COLOR_KINDS = ("red", "green", "blue")


def hsb_to_rgb(h: float, s: float, b: float) -> tuple[int, int, int]:
    """h 0-360, s e b 0-1 -> RGB 0-255."""
    r, g, bl = colorsys.hsv_to_rgb((h % 360) / 360.0, max(0, min(1, s)), max(0, min(1, b)))
    return round(r * 255), round(g * 255), round(bl * 255)


def rgb_to_hsb(r: int, g: int, b: int) -> tuple[float, float, float]:
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s, v


def _channel_name(engine: LightEngine, fixture: str, kind: str) -> str | None:
    c = engine.project.patch.find(fixture).profile.channel_of_kind(kind)
    return c.name if c else None


def set_color(engine: LightEngine, fixtures: list[str], rgb: tuple[int, int, int]) -> None:
    """Imposta il colore sui fixture che hanno canali colore.

    Fixture con solo dimmer: la luminosità segue il valore massimo del colore (come Lightkey).
    """
    for name in fixtures:
        names = [_channel_name(engine, name, k) for k in COLOR_KINDS]
        if all(names):
            for n, v in zip(names, rgb):
                engine.set_value(name, n, v)
            white = _channel_name(engine, name, "white")
            if white:
                engine.set_value(name, white, min(rgb))   # il bianco ripete la parte neutra
        else:
            dim = _channel_name(engine, name, "intensity")
            if dim:
                engine.set_value(name, dim, max(rgb))


def set_dimmer(engine: LightEngine, fixtures: list[str], value: int, relative: bool = False) -> None:
    """Assoluto: stesso valore a tutti. Relativo: `value` (-255..255) si somma al valore di ciascuno."""
    for name in fixtures:
        ch = _channel_name(engine, name, "intensity")
        if ch:
            cur = engine.get_value(name, ch)
            engine.set_value(name, ch, max(0, min(255, cur + value if relative else value)))
        else:   # senza dimmer: agisce sulla luminosità RGB
            names = [_channel_name(engine, name, k) for k in COLOR_KINDS]
            if all(names):
                vals = [engine.get_value(name, n) for n in names]
                top = max(vals) or 1
                target = max(0, min(255, (top + value) if relative else value))
                if max(vals) == 0:
                    vals = [255, 255, 255]; top = 255   # nero: parte dal bianco
                for n, v in zip(names, vals):
                    engine.set_value(name, n, round(v * target / top))


def override_state(engine: LightEngine, fixtures: list[str], channel: str) -> str:
    """"none" | "some" | "all": quanti dei fixture (che hanno il canale) lo hanno definito."""
    have = [f for f in fixtures
            if any(c.name == channel for c in engine.project.patch.find(f).profile.channels)]
    if not have:
        return "none"
    n = sum(1 for f in have if channel in engine.values.get(f, {}))
    return "none" if n == 0 else "all" if n == len(have) else "some"


def clear_override(engine: LightEngine, fixtures: list[str], channel: str | None = None) -> None:
    """Toglie l'override di un canale (o di tutti) dai fixture indicati."""
    for name in fixtures:
        fx = engine.project.patch.find(name)
        chans = [channel] if channel else list(engine.values.get(name, {}))
        for ch in chans:
            if ch in engine.values.get(name, {}):
                del engine.values[name][ch]
                for dmx in fx.channel_values({ch: 0}):
                    engine.programmer.release(fx.universe, dmx)
