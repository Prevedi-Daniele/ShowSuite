"""Elementi scenici del Preview (tralicci, linee, testi) e allineamento dei fixture."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StageShape:
    kind: str                 # "truss" | "line" | "text" | "rect" | "ellipse" | "ledstrip"
    x1: float
    y1: float
    x2: float = 0.0
    y2: float = 0.0
    text: str = ""
    color: str = "#c8cad4"
    bulge: float = 0.0        # curvatura: 0 = dritto; ±1 = freccia pari alla lunghezza della corda

    def control(self) -> tuple[float, float]:
        mx, my = (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        return mx - dy * self.bulge, my + dx * self.bulge     # normale alla corda, lato "sinistro"

    def points(self, n: int = 40) -> list[tuple[float, float]]:
        """Polilinea lungo la forma (Bézier quadratica se curva)."""
        if self.kind == "text":
            return [(self.x1, self.y1), (self.x2, self.y2)]
        if self.kind in ("rect", "ellipse"):
            return self._outline()
        cx, cy = self.control(); out = []
        for i in range(n + 1):
            t = i / n; u = 1 - t
            out.append((u * u * self.x1 + 2 * u * t * cx + t * t * self.x2,
                        u * u * self.y1 + 2 * u * t * cy + t * t * self.y2))
        return out

    def _outline(self, n: int = 24) -> list[tuple[float, float]]:
        """Contorno chiuso: ellisse inscritta, o rettangolo con angoli arrotondati (bulge = raggio 0-1)."""
        import math
        x0, y0, x1, y1 = self.bounds(); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; a, b = (x1 - x0) / 2, (y1 - y0) / 2
        if self.kind == "ellipse":
            return [(cx + a * math.cos(2 * math.pi * i / 48), cy + b * math.sin(2 * math.pi * i / 48)) for i in range(49)]
        r = max(0.0, min(1.0, abs(self.bulge))) * min(a, b)
        if r <= 1e-9:
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        pts = []
        for (ox, oy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            for k in range(7):
                t = math.radians(a0 + 90 * k / 6); pts.append((ox + r * math.cos(t), oy + r * math.sin(t)))
        pts.append(pts[0]); return pts

    def bounds(self) -> tuple[float, float, float, float]:
        return (min(self.x1, self.x2), min(self.y1, self.y2), max(self.x1, self.x2), max(self.y1, self.y2))

    def distance(self, x: float, y: float) -> float:
        """Distanza (in coordinate normalizzate) dal punto; per il testo dal suo punto di ancoraggio."""
        if self.kind == "text":
            return ((x - self.x1) ** 2 + (y - self.y1) ** 2) ** 0.5
        pts = self.points(); best = 1e9
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = bx - ax, by - ay
            l2 = dx * dx + dy * dy
            t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
            best = min(best, ((x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2) ** 0.5)
        return best

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


def duplicate_shape(shapes: list, sh, dx: float = 0.03, dy: float = 0.03):
    """Copia la forma (spostata di dx,dy) subito sopra l'originale nell'ordine di sovrapposizione."""
    import dataclasses
    new = dataclasses.replace(sh, x1=sh.x1 + dx, y1=sh.y1 + dy, x2=sh.x2 + dx, y2=sh.y2 + dy)
    shapes.insert(shapes.index(sh) + 1, new)
    return new


def reorder_shape(shapes: list, sh, where: str) -> None:
    """where: front | back | up | down (l'ultimo della lista è disegnato sopra)."""
    i = shapes.index(sh); shapes.pop(i)
    j = {"front": len(shapes), "back": 0, "up": min(i + 1, len(shapes)), "down": max(i - 1, 0)}[where]
    shapes.insert(j, sh)
