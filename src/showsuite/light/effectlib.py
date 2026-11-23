"""Libreria di effetti colore predefiniti (swatch o curve) per il pannello Effetti."""
from __future__ import annotations

from copy import deepcopy

from .colorfx import ColorEffect, hue_wheel


def _sw(duration, *cols, offset=0.1, cross=True):
    return ColorEffect("swatches", [tuple(c) for c in cols], duration=duration, time_offset=offset, crossfade=cross)


COLOR_LIBRARY: dict[str, ColorEffect] = {
    "Fire": _sw(1.2, (255, 40, 0), (255, 120, 0), (255, 200, 20), (200, 20, 0), offset=0.3),
    "Rainbow": ColorEffect("curves", hue=hue_wheel(), saturation=[(0, 1.0)], brightness=[(0, 1.0)], duration=6.0, time_offset=0.25),
    "Ocean": _sw(8.0, (0, 40, 160), (0, 140, 200), (0, 200, 190), (10, 60, 120), offset=0.3),
    "Police": _sw(0.5, (255, 0, 0), (0, 0, 255), offset=0.5, cross=False),
    "Candy": _sw(4.0, (255, 60, 160), (255, 160, 220), (120, 220, 255), (255, 255, 160), offset=0.2),
    "Purple Rain": _sw(3.0, (110, 0, 220), (200, 60, 255), (60, 0, 140), offset=0.4),
    "Green Boas": _sw(5.0, (0, 255, 60), (120, 255, 0), (0, 160, 40), offset=0.3),
    "Glittering Snow": _sw(0.8, (255, 255, 255), (180, 210, 255), (255, 255, 255), (120, 160, 255), offset=0.5, cross=False),
    "Sparkle": _sw(0.6, (255, 255, 255), (0, 0, 0), (255, 220, 120), (0, 0, 0), offset=0.7, cross=False),
    "Sunset": _sw(10.0, (255, 90, 0), (255, 40, 80), (140, 0, 120), (30, 0, 90), offset=0.2),
    "Ice": _sw(6.0, (200, 240, 255), (80, 180, 255), (255, 255, 255), offset=0.2),
    "K.I.T.T.": _sw(2.0, (255, 0, 0), (60, 0, 0), (255, 0, 0), offset=0.6),
}


def search(query: str) -> list[str]:
    q = query.strip().lower()
    return [n for n in COLOR_LIBRARY if q in n.lower()]


def get(name: str) -> ColorEffect:
    """Copia indipendente dell'effetto (modificabile senza toccare la libreria)."""
    return deepcopy(COLOR_LIBRARY[name])
