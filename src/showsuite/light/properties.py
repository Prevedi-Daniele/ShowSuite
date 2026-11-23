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


# ---------------------------------------------------------------- proprietà del Design view
PROPERTY_ORDER = ("dimmer", "color", "color_wheel", "gobo_wheel", "shutter", "position",
                  "zoom", "focus", "iris", "prism", "frost")
SHORTCUTS = {"dimmer": "D", "color": "C", "color_wheel": "C", "gobo_wheel": "G", "position": "P",
             "shutter": "S", "prism": "M", "focus": "F", "zoom": "Z", "iris": "I", "frost": "R"}
PROPERTY_TITLES = {"dimmer": "Dimmer", "color": "Color", "color_wheel": "Color Wheel",
                   "gobo_wheel": "Gobo Wheel", "shutter": "Shutter/Strobe", "position": "Position",
                   "zoom": "Zoom", "focus": "Focus", "iris": "Iris", "prism": "Prism", "frost": "Frost"}
_COLOR_KINDS = ("red", "green", "blue", "white", "amber", "uv")


def property_channels(profile, prop: str) -> list[str]:
    """Nomi dei canali che compongono una proprietà (per lo stato override)."""
    ch = profile.channels
    by = lambda *kinds: [c.name for c in ch if c.kind in kinds]
    if prop == "dimmer":
        return by("intensity") or by("red", "green", "blue")
    if prop == "color":
        return by(*_COLOR_KINDS)
    if prop == "position":
        return by("pan", "tilt")
    return by(prop) if prop != "color_wheel" else by("color_wheel")


def available_properties(profile) -> list[str]:
    """Proprietà mostrate nel Design view per un profilo, nell'ordine standard."""
    out = []
    for prop in PROPERTY_ORDER:
        if prop == "dimmer":
            ok = bool(property_channels(profile, "dimmer"))
        elif prop == "color":
            ok = all(profile.channel_of_kind(k) for k in COLOR_KINDS)
        elif prop == "position":
            ok = profile.channel_of_kind("pan") is not None or profile.channel_of_kind("tilt") is not None
        else:
            ok = profile.channel_of_kind(prop) is not None
        if ok:
            out.append(prop)
    return out


def property_state(engine: LightEngine, fixtures: list[str], prop: str) -> str:
    """"none" | "some" | "all" per un'intera proprietà (punto blu / grigio)."""
    states = []
    for f in fixtures:
        prof = engine.project.patch.find(f).profile
        names = property_channels(prof, prop)
        if names:
            states.append(any(n in engine.values.get(f, {}) for n in names))
    if not states:
        return "none"
    return "all" if all(states) else "some" if any(states) else "none"


def clear_property(engine: LightEngine, fixtures: list[str], prop: str) -> None:
    for f in fixtures:
        prof = engine.project.patch.find(f).profile
        for n in property_channels(prof, prop):
            clear_override(engine, [f], n)


def wheel_slots(profile, kind: str) -> list[tuple[int, str]]:
    """[(valore DMX centrale, etichetta)] per ruota colori o gobo."""
    c = profile.channel_of_kind(kind)
    return [((lo + hi) // 2, label) for lo, hi, _t, label in (c.caps if c else ())]


def set_slot(engine: LightEngine, fixtures: list[str], kind: str, index: int) -> int:
    """Seleziona lo slot `index` di una ruota sui fixture che la possiedono. Restituisce quanti ha impostato."""
    n = 0
    for f in fixtures:
        prof = engine.project.patch.find(f).profile
        slots = wheel_slots(prof, kind)
        c = prof.channel_of_kind(kind)
        if c and 0 <= index < len(slots):
            engine.set_value(f, c.name, slots[index][0]); n += 1
    return n


def set_shutter(engine: LightEngine, fixtures: list[str], state: str, speed: float = 0.5) -> int:
    """state: "open" | "closed" | "strobe" (speed 0-1 dentro l'intervallo dello strobo)."""
    n = 0
    for f in fixtures:
        prof = engine.project.patch.find(f).profile
        c = prof.channel_of_kind("shutter")
        if not c:
            continue
        rng = next(((lo, hi) for lo, hi, _t, label in c.caps if label.lower() == state), None)
        if rng is None:
            continue
        lo, hi = rng
        engine.set_value(f, c.name, round(lo + (hi - lo) * speed) if state == "strobe" else (lo + hi) // 2)
        n += 1
    return n


def set_simple(engine: LightEngine, fixtures: list[str], kind: str, value: float) -> int:
    """Proprietà continue (zoom, focus, iris, frost, prism...): value 0-1."""
    n = 0
    for f in fixtures:
        c = engine.project.patch.find(f).profile.channel_of_kind(kind)
        if c:
            engine.set_value(f, c.name, round(max(0, min(1, value)) * (65535 if c.fine else 255))); n += 1
    return n


def set_position(engine: LightEngine, fixtures: list[str], pan: float | None = None,
                 tilt: float | None = None) -> int:
    """pan/tilt normalizzati 0-1 (0.5 = centro)."""
    n = 0
    for f in fixtures:
        prof = engine.project.patch.find(f).profile
        for kind, v in (("pan", pan), ("tilt", tilt)):
            c = prof.channel_of_kind(kind)
            if c and v is not None:
                engine.set_value(f, c.name, round(max(0, min(1, v)) * (65535 if c.fine else 255))); n += 1
    return n


def copy_properties(engine: LightEngine, fixture: str) -> dict[str, int]:
    """Valori del programmer del fixture, indicizzati per tipo di canale (o nome se senza tipo)."""
    prof = engine.project.patch.find(fixture).profile
    out = {}
    for c in prof.channels:
        if c.name in engine.values.get(fixture, {}):
            out[c.kind or c.name] = engine.values[fixture][c.name]
    return out


def paste_properties(engine: LightEngine, fixtures: list[str], data: dict[str, int]) -> int:
    n = 0
    for f in fixtures:
        for c in engine.project.patch.find(f).profile.channels:
            k = c.kind or c.name
            if k in data:
                engine.set_value(f, c.name, data[k]); n += 1
    return n


def reset_to_default(engine: LightEngine, fixtures: list[str]) -> None:
    for f in fixtures:
        engine.values.pop(f, None)
