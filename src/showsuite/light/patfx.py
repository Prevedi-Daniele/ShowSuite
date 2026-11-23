"""Effetti a pattern di Lightkey: Chase, Scanner, Yo-yo, Fill, Rain, Meteor, Sparkle, Fire, Jellyfish, Snakes.

Ogni fixture è un "pixel"; l'ordine dei pixel dipende dall'ordine scelto (sinistra-destra, per nome...).
Il primo campione (sample) è lo sfondo nei pattern che lo prevedono; gli altri colorano gli elementi in movimento.
Tutto è deterministico (random con seme) così l'anteprima e l'uscita coincidono.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

RGB = tuple[int, int, int]

PATTERNS = ("chase", "scanner", "yoyo", "fill", "rain", "meteor", "sparkle", "fire", "jellyfish", "snakes")
PATTERN_TITLES = {"chase": "Chase", "scanner": "Scanner", "yoyo": "Yo-yo", "fill": "Fill", "rain": "Rain",
                  "meteor": "Meteor", "sparkle": "Sparkle", "fire": "Fire", "jellyfish": "Jellyfish", "snakes": "Snakes"}
ORDERS = ("left_right", "right_left", "top_bottom", "bottom_top", "name", "name_desc", "address",
          "address_desc", "random_fixed", "custom")
ORDER_TITLES = {"left_right": "Left to Right", "right_left": "Right to Left", "top_bottom": "Top to Bottom",
                "bottom_top": "Bottom to Top", "name": "By Short Name", "name_desc": "By Short Name (desc.)",
                "address": "By Address", "address_desc": "By Address (desc.)", "random_fixed": "Random (Fixed)",
                "custom": "Custom Order"}
ORIGINS = ("start_end", "from_center", "to_center")

# parametri di ogni pattern con i valori predefiniti (come nel manuale)
DEFAULTS: dict[str, dict[str, float]] = {
    "chase": {"steps_per_value": 1, "phase": 0.0, "time_offset": 0.0, "delay": 0.0, "smoothness": 0.0},
    "scanner": {"length": 1, "overshoot": 0, "phase": 0.0, "fringe": 0.0, "noise": 0.0},
    "yoyo": {"phase": 0.0, "center": 0.5, "steepness": 0.0},
    "fill": {"phase": 0.0, "center": 0.5, "steepness": 0.0},
    "rain": {"length": 3, "distance": 3, "phase": 0.0, "fringe": 0.0, "noise": 0.0},
    "meteor": {"length": 1, "distance": 6, "phase": 0.0, "trail": 4, "fringe": 1.0, "noise": 0.3, "palette": 0},
    "sparkle": {"interval": 0.15, "lifetime": 0.6, "fringe": 1.0, "noise": 0.0, "palette": 0},
    "fire": {"speed": 1.0, "sparking": 0.5, "cooling": 0.5},
    "jellyfish": {"count": 3, "size": 4.0, "speed": 1.0, "fringe": 0.5, "palette": 1},
    "snakes": {"speed": 1.0},
}
RANDOM_TIMED = ("sparkle", "fire")          # non seguono la durata ma il tempo reale
Sample = tuple[int, int, int]


def _mix(a: RGB, b: RGB, k: float) -> RGB:
    k = max(0.0, min(1.0, k))
    return (round(a[0] + (b[0] - a[0]) * k), round(a[1] + (b[1] - a[1]) * k), round(a[2] + (b[2] - a[2]) * k))


def _tri(x: float) -> float:
    x %= 1.0
    return 1 - abs(2 * x - 1)


def _palette(samples: list[RGB], x: float) -> RGB:
    """Colore a posizione x (0-1) interpolando fra i campioni."""
    if len(samples) == 1:
        return samples[0]
    x = max(0.0, min(1.0, x)) * (len(samples) - 1)
    i = min(int(x), len(samples) - 2)
    return _mix(samples[i], samples[i + 1], x - i)


@dataclass
class PatternEffect:
    pattern: str = "chase"
    samples: list[Sample] = field(default_factory=lambda: [(255, 0, 0), (0, 0, 255)])
    params: dict[str, float] = field(default_factory=dict)
    duration: float = 1.0                 # durata (s) di un ciclo / di un campione
    beat_controlled: bool = False
    beat_mult: float = 1.0                # moltiplicatore di battuta (2 = due cicli a battuta)
    order: str = "left_right"
    origin: str = "start_end"
    grouping: int = 1
    repeat: int = 0                       # 0 = nessuna ripetizione
    custom_order: dict[str, int] = field(default_factory=dict)
    seed: int = 1

    def p(self, key: str) -> float:
        return self.params.get(key, DEFAULTS[self.pattern][key])

    # --- ordine dei pixel
    def pixel_indices(self, fixtures: list) -> dict[str, int]:
        """nome fixture -> indice di pixel (fixture con lo stesso indice si comportano come un pixel)."""
        if self.order == "custom":
            base = {f.name: self.custom_order.get(f.name, i) for i, f in enumerate(fixtures)}
            levels = {v: k for k, v in enumerate(sorted(set(base.values())))}
            return {n: levels[v] for n, v in base.items()}      # numeri uguali = stesso pixel
        keys = {"left_right": lambda f: (f.x, f.y), "right_left": lambda f: (-f.x, f.y),
                "top_bottom": lambda f: (f.y, f.x), "bottom_top": lambda f: (-f.y, f.x),
                "name": lambda f: f.name.lower(), "address": lambda f: (f.universe, f.address)}
        if self.order == "random_fixed":
            r = random.Random(self.seed); idx = list(range(len(fixtures))); r.shuffle(idx)
            ordered = [fixtures[i] for i in sorted(range(len(fixtures)), key=lambda i: idx[i])]
        elif self.order.endswith("_desc"):
            ordered = sorted(fixtures, key=keys[self.order[:-5]], reverse=True)
        else:
            ordered = sorted(fixtures, key=keys[self.order])
        n = len(ordered)
        pos = list(range(n))
        if self.origin != "start_end" and self.order != "random_fixed":
            c = (n - 1) / 2
            pos = sorted(range(n), key=lambda i: abs(i - c))      # centro -> bordi
            rank = {i: k for k, i in enumerate(pos)}
            pos = [rank[i] for i in range(n)]
            if self.origin == "to_center":
                pos = [n - 1 - p for p in pos]
        out = {}
        for i, f in enumerate(ordered):
            k = pos[i] // max(1, self.grouping)
            out[f.name] = k % self.repeat if self.repeat > 1 else k
        return out

    # --- valutazione
    def cycle(self, t: float, beats: float = 0.0) -> float:
        """Posizione nel ciclo (in cicli, con la fase)."""
        base = beats * self.beat_mult if self.beat_controlled else t / max(1e-6, self.duration)
        return base + (self.p("phase") if "phase" in DEFAULTS[self.pattern] else 0.0)

    def evaluate(self, fixtures: list, t: float, beats: float = 0.0) -> dict[str, RGB]:
        if not fixtures:
            return {}
        idx = self.pixel_indices(fixtures)
        n = max(idx.values()) + 1
        c = self.cycle(t, beats)
        cols = self.pixels(n, c, t)
        return {name: cols[i] for name, i in idx.items()}

    def pixels(self, n: int, c: float, t: float = 0.0) -> list[RGB]:
        S = self.samples or [(0, 0, 0)]
        bg = S[0]; fg = S[1:] or [S[0]]
        fn = getattr(self, f"_p_{self.pattern}")
        return fn(n, c, t, S, bg, fg)

    # --- pattern
    def _p_chase(self, n, c, t, S, bg, fg):
        k = len(S); spv = max(1, int(self.p("steps_per_value"))); out = []
        off, delay, smooth = self.p("time_offset"), self.p("delay"), self.p("smoothness")
        for i in range(n):
            pos = c - i * off - i * delay
            if i * delay > 0 and c < i * delay:       # il ritardo: all'inizio ogni pixel resta sul primo campione
                out.append(S[0]); continue
            if delay > 0:
                pos = c - i * delay - i * off
            s = pos / spv
            j = math.floor(s); frac = s - j
            a, b = S[j % k], S[(j + 1) % k]
            out.append(_mix(a, b, (frac - (1 - smooth)) / smooth) if smooth > 0 else a)
        return out

    def _p_scanner(self, n, c, t, S, bg, fg):
        L, ov, fr, noise = self.p("length"), self.p("overshoot"), self.p("fringe"), self.p("noise")
        eye = fg[int(math.floor(c)) % len(fg)]
        span = (n - 1) + 2 * ov
        x = -ov + span * _tri(c / 2)
        out = []
        for i in range(n):
            d = abs(i - x); half = L / 2
            edge = half + fr * max(1.0, half)                    # il bordo sfumato (fringe) si estende oltre l'occhio
            w = 1.0 if d <= half else (max(0.0, 1 - (d - half) / (edge - half)) if fr > 0 else 0.0)
            if fr > 0 and noise and w < 1.0:
                w *= 1 - noise * random.Random(i * 31 + int(c * 8)).random()
            out.append(_mix(bg, eye, w))
        return out

    def _fillish(self, n, c, bg, fg, yoyo: bool):
        center, steep = self.p("center"), self.p("steepness")
        k = int(math.floor(c)); x = c - k
        col = fg[k % len(fg)]
        if yoyo:
            prog = _tri(x) ** (1 + 3 * steep)          # sale e scende
        else:
            prog = (x / center if x < center else 1.0 - (x - center) / max(1e-6, 1 - center)) if center < 1 else x
            prog = max(0.0, min(1.0, prog)) ** (1 + 3 * steep)
        return [col if (i + 0.5) / n <= prog else bg for i in range(n)]

    def _p_yoyo(self, n, c, t, S, bg, fg):
        return self._fillish(n, c, bg, fg, True)

    def _p_fill(self, n, c, t, S, bg, fg):
        return self._fillish(n, c, bg, fg, False)

    def _streaks(self, n, c, bg, fg, L, D, fringe, noise, trail=0):
        period = max(1, L + D); out = [bg] * n
        shift = c * period                                      # un periodo per ciclo
        for i in range(n):
            u = (i - shift) % period                            # posizione relativa alla testa (cresce verso la coda)
            k = int(math.floor((i - shift) / period))          # indice della scia
            col = fg[k % len(fg)] if not self.p_has("palette") or not self.p("palette") else _palette(fg, (k % 7) / 6)
            if u < L:
                w = 1.0 if fringe == 0 else 1 - fringe * 0.5 * (u / max(1, L))
            elif trail and u < L + trail:
                w = (1 - (u - L + 1) / (trail + 1)) * (fringe if fringe else 1.0)
                if noise:
                    w *= 1 - noise * random.Random(i * 97 + k * 13).random()
            else:
                continue
            out[i] = _mix(bg, col, w)
        return out

    def p_has(self, key: str) -> bool:
        return key in DEFAULTS[self.pattern]

    def _p_rain(self, n, c, t, S, bg, fg):
        return self._streaks(n, -c, bg, fg, int(self.p("length")), int(self.p("distance")), self.p("fringe"), self.p("noise"))

    def _p_meteor(self, n, c, t, S, bg, fg):
        return self._streaks(n, -c, bg, fg, int(self.p("length")), int(self.p("distance")), self.p("fringe"),
                             self.p("noise"), int(self.p("trail")))

    def _p_sparkle(self, n, c, t, S, bg, fg):
        interval, life = max(0.01, self.p("interval")), max(0.01, self.p("lifetime"))
        fr, noise = self.p("fringe"), self.p("noise")
        out = [bg] * n
        first = int(max(0, math.floor((t - life) / interval)))
        for k in range(first, int(math.floor(t / interval)) + 1):
            r = random.Random(self.seed * 1000003 + k)
            i = r.randrange(n); age = t - k * interval
            if not 0 <= age <= life:
                continue
            col = _palette(fg, age / life) if self.p("palette") else fg[k % len(fg)]
            w = 1.0 if fr == 0 else 1 - fr * (age / life)
            if noise:
                w *= 1 - noise * r.random()
            out[i] = _mix(out[i], col, w)
        return out

    @staticmethod
    def _noise(x: float, seed: int) -> float:
        i = math.floor(x); f = x - i; f = f * f * (3 - 2 * f)
        a = random.Random(seed * 7919 + i).random(); b = random.Random(seed * 7919 + i + 1).random()
        return a + (b - a) * f

    def _p_fire(self, n, c, t, S, bg, fg):
        speed, spark, cool = self.p("speed"), self.p("sparking"), self.p("cooling")
        out = []
        for i in range(n):
            base = 1 - i / max(1, n - 1) if n > 1 else 1.0          # il fuoco è più caldo alla base (primo pixel)
            h = base ** (1 + cool * 2) * (0.55 + 0.9 * spark * self._noise(t * 6 * speed + i * 0.7, self.seed + i))
            h += 0.25 * (self._noise(t * 11 * speed - i * 1.3, self.seed + 99) - 0.5)
            out.append(_palette(S, h))
        return out

    def _p_jellyfish(self, n, c, t, S, bg, fg):
        count, size, speed, fr = int(self.p("count")), self.p("size"), self.p("speed"), self.p("fringe")
        out = [bg] * n
        for j in range(max(1, count)):
            r = random.Random(self.seed * 131 + j)
            x = (r.random() * n + t * speed * (1 + r.random())) % n
            sz = size * (0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 2 * speed + j * 2.1)))
            col = _palette(fg, (j % 5) / 4) if self.p("palette") else fg[j % len(fg)]
            for i in range(n):
                d = min(abs(i - x), n - abs(i - x))
                if d < sz:
                    w = 1 - fr * (d / sz)
                    out[i] = _mix(out[i], col, w)
        return out

    def _p_snakes(self, n, c, t, S, bg, fg):
        r = random.Random(self.seed); segs = []; total = 0
        for k in range(32):
            L, g = r.randint(1, 5), r.randint(2, 6)
            segs.append((total, L, fg[k % len(fg)])); total += L + g
        shift = (c * total) % total
        out = [bg] * n
        for i in range(n):
            x = (i - shift) % total
            for start, L, col in segs:
                if start <= x < start + L:
                    out[i] = col; break
        return out

    # --- applicazione
    def apply(self, engine, fixtures: list[str], t: float, beats: float = 0.0) -> None:
        from . import properties as P
        patch = engine.project.patch
        fx = [patch.find(n) for n in fixtures]
        for name, rgb in self.evaluate(fx, t, beats).items():
            P.set_color(engine, [name], rgb)
