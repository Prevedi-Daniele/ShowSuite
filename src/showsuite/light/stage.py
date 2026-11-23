"""Elementi scenici del Preview (tralicci, linee, testi) e allineamento dei fixture."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StageShape:
    kind: str                 # "truss" | "line" | "text"
    x1: float
    y1: float
    x2: float = 0.0
    y2: float = 0.0
    text: str = ""
    color: str = "#c8cad4"

    def bounds(self) -> tuple[float, float, float, float]:
        return (min(self.x1, self.x2), min(self.y1, self.y2), max(self.x1, self.x2), max(self.y1, self.y2))

    def distance(self, x: float, y: float) -> float:
        """Distanza (in coordinate normalizzate) dal punto; per il testo dal suo punto di ancoraggio."""
        if self.kind == "text":
            return ((x - self.x1) ** 2 + (y - self.y1) ** 2) ** 0.5
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - self.x1) * dx + (y - self.y1) * dy) / l2))
        px, py = self.x1 + t * dx, self.y1 + t * dy
        return ((x - px) ** 2 + (y - py) ** 2) ** 0.5

    def move(self, dx: float, dy: float) -> None:
        self.x1 += dx; self.x2 += dx; self.y1 += dy; self.y2 += dy


ALIGN_MODES = ("left", "right", "top", "bottom", "hcenter", "vcenter")


def align(fixtures, mode: str) -> None:
    """Allinea i fixture (con x,y normalizzati)."""
    if len(fixtures) < 2:
        return
    if mode == "left":
        v = min(f.x for f in fixtures); [setattr(f, "x", v) for f in fixtures]
    elif mode == "right":
        v = max(f.x for f in fixtures); [setattr(f, "x", v) for f in fixtures]
    elif mode == "top":
        v = min(f.y for f in fixtures); [setattr(f, "y", v) for f in fixtures]
    elif mode == "bottom":
        v = max(f.y for f in fixtures); [setattr(f, "y", v) for f in fixtures]
    elif mode == "hcenter":
        v = (min(f.x for f in fixtures) + max(f.x for f in fixtures)) / 2; [setattr(f, "x", v) for f in fixtures]
    elif mode == "vcenter":
        v = (min(f.y for f in fixtures) + max(f.y for f in fixtures)) / 2; [setattr(f, "y", v) for f in fixtures]
    else:
        raise ValueError(f"allineamento sconosciuto: {mode}")


def distribute(fixtures, axis: str) -> None:
    """Distribuisce uniformemente fra il primo e l'ultimo (per posizione) lungo "h" o "v"."""
    if len(fixtures) < 3:
        return
    key = (lambda f: f.x) if axis == "h" else (lambda f: f.y)
    attr = "x" if axis == "h" else "y"
    fs = sorted(fixtures, key=key)
    a, b = key(fs[0]), key(fs[-1])
    for i, f in enumerate(fs):
        setattr(f, attr, a + (b - a) * i / (len(fs) - 1))


@dataclass
class FixtureGroup:
    name: str
    fixtures: list[str]


def make_group(groups: list[FixtureGroup], name: str, fixtures: list[str]) -> FixtureGroup:
    """Crea o sostituisce il gruppo `name` (l'ordine dei fixture è quello di selezione)."""
    name = name.strip()
    if not name:
        raise ValueError("nome gruppo vuoto")
    if not fixtures:
        raise ValueError("selezione vuota")
    groups[:] = [g for g in groups if g.name != name]
    g = FixtureGroup(name, list(dict.fromkeys(fixtures)))
    groups.append(g)
    return g


def select_by_profile(patch, fixture_name: str) -> list[str]:
    """Tutti i fixture dello stesso tipo (costruttore, modello e modalità) del fixture dato."""
    ref = patch.find(fixture_name).profile
    key = (ref.manufacturer, ref.model, ref.mode)
    return [f.name for f in patch.fixtures if (f.profile.manufacturer, f.profile.model, f.profile.mode) == key]
