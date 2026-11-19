"""Live: cue con preset ed effetti, fade e priorità."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .dmx.mixer import Mixer
from .effects import Effect
from .preset import Preset

CURVES = {
    "linear": lambda x: x,
    "ease_in": lambda x: x * x,
    "ease_out": lambda x: 1 - (1 - x) ** 2,
    "s_curve": lambda x: x * x * (3 - 2 * x),
}


@dataclass
class LiveCue:
    name: str
    fixtures: list[str]
    preset: Preset | None = None
    effects: list[Effect] = field(default_factory=list)
    fade_in: float = 0.0        # secondi
    fade_out: float = 0.0
    curve: str = "linear"
    priority: int = 10          # più alto vince (come Mixer.Layer)
    toggle: bool = True
    # Sequenza: se `steps` non è vuoto i preset si alternano a tempo di battuta
    steps: list[Preset] = field(default_factory=list)
    beats_per_step: float = 1.0
    crossfade: float = 0.0      # frazione dello step (0-1) usata per sfumare verso il successivo
    loop: bool = True
    # Modificatori (vivi): speed moltiplica la velocità di effetti e sequenze; dimmer scala l'intensità
    speed: float = 1.0
    dimmer: float = 1.0


PAGE_PRIORITY_STEP = 100   # priorità effettiva = pagina * 100 + priorità del cue (0-99)


@dataclass
class CueListStep:
    cue: str
    hold: float | None = None   # None = manuale (aspetta GO); altrimenti secondi dopo il fade
    fade: float = 0.0
    curve: str = "linear"
    skip: bool = False


@dataclass
class CueList:
    name: str
    steps: list[CueListStep] = field(default_factory=list)
    loop: bool = False
    priority: int = 10


@dataclass
class LiveButton:
    cue: str                    # nome del cue
    mode: str = "toggle"        # "toggle" | "flash" (attivo solo finché premuto)
    color: str = "#3a7bd5"
    label: str = ""


@dataclass
class LivePage:
    name: str
    buttons: list[LiveButton] = field(default_factory=list)
    priority: int = 0           # 0-99: tra pagine vince la più alta
    fade_time: float = 0.0      # secondi, cambio pagina
    columns: int = 6
    cuelist: CueList | None = None   # una cuelist per pagina


class LivePlayer:
    """Gestisce i cue attivi; `update` scrive nei layer del mixer."""

    def __init__(self, engine, now):
        self.engine = engine
        self._now = now
        self.active: dict[str, dict] = {}   # nome cue -> stato
        self._layers: dict[int, object] = {}
        self._cl: dict[str, dict] = {}   # stato delle cuelist in esecuzione

    def trigger(self, cue: LiveCue, page_priority: int = 0) -> None:
        with self.engine.mixer.lock:
            self._trigger(cue, page_priority)

    def start(self, cue: LiveCue, page_priority: int = 0) -> None:
        """Avvia sempre (mai toggle): per i pulsanti Flash."""
        with self.engine.mixer.lock:
            self.active.pop(cue.name, None)
            self._begin(cue, page_priority)

    def _trigger(self, cue: LiveCue, page_priority: int = 0) -> None:
        st = self.active.get(cue.name)
        if st and cue.toggle and not st["releasing"]:
            return self.release(cue)
        self.active.pop(cue.name, None)   # rientra in coda: a parità vince il più recente
        self._begin(cue, page_priority)

    def _begin(self, cue: LiveCue, page_priority: int) -> None:
        self.active[cue.name] = {"cue": cue, "t0": self._now(), "releasing": False, "t1": 0.0,
                                 "b0": self.engine.beat.beats(), "bp": self.engine.beat.beats(),
                                 "bl": self.engine.beat.beats(),
                                 "prio": page_priority * PAGE_PRIORITY_STEP + cue.priority}

    def release(self, cue: LiveCue, fade: float | None = None, curve: str | None = None) -> None:
        st = self.active.get(cue.name)
        if st and not st["releasing"]:
            st.update(releasing=True, t1=self._now(), fo=fade, curve_o=curve)

    def _level(self, st) -> float:
        cue, now = st["cue"], self._now()
        if st["releasing"]:
            fo = st.get("fo")
            fo = cue.fade_out if fo is None else fo
            f = CURVES[st.get("curve_o") or cue.curve]
            if fo <= 0:
                return 0.0
            return f(max(0.0, 1 - (now - st["t1"]) / fo))
        f = CURVES[cue.curve]
        if cue.fade_in <= 0:
            return 1.0
        return f(min(1.0, (now - st["t0"]) / cue.fade_in))

    @staticmethod
    def _step_values(cue: LiveCue, st: dict, beats: float) -> dict[str, float]:
        n = len(cue.steps)
        pos = max(0.0, (beats - st["b0"]) / cue.beats_per_step)
        idx = int(pos)
        frac = pos - idx
        if not cue.loop and idx >= n:
            return dict(cue.steps[-1].values)
        cur, nxt = cue.steps[idx % n], cue.steps[(idx + 1) % n]
        out = dict(cur.values)
        if cue.crossfade > 0 and (cue.loop or idx + 1 < n):
            start = 1.0 - cue.crossfade
            if frac > start:
                t = (frac - start) / cue.crossfade
                for ch in set(cur.values) | set(nxt.values):
                    a, b = cur.values.get(ch, 0), nxt.values.get(ch, 0)
                    out[ch] = a + (b - a) * t
        return out

    def update(self) -> None:
        with self.engine.mixer.lock:
            self._update()

    def _update(self) -> None:
        """Ricalcola i layer del mixer da zero in base ai cue attivi."""
        for layer in self._layers.values():
            layer.clear()
        beats = self.engine.beat.beats()
        patch = self.engine.project.patch
        self._tick_cuelists()
        for name in list(self.active):
            st = self.active[name]
            st["bp"] += (beats - st["bl"]) * st["cue"].speed   # la velocità cambia senza salti di fase
            st["bl"] = beats
            level = self._level(st)
            if st["releasing"] and level <= 0:
                del self.active[name]
                continue
            cue = st["cue"]
            prio = st.get("prio", cue.priority)
            layer = self._layers.get(prio)
            if layer is None:
                layer = self._layers[prio] = self.engine.mixer.add_layer(prio)
            values: list[tuple[str, str, float]] = []
            if cue.preset:
                for fx_name in cue.fixtures:
                    for ch, v in cue.preset.values.items():
                        values.append((fx_name, ch, v))
            if cue.steps:
                for fx_name in cue.fixtures:
                    for ch, v in self._step_values(cue, st, st["bp"]).items():
                        values.append((fx_name, ch, v))
            for eff in cue.effects:
                for fx_name, v in eff.evaluate(cue.fixtures, st["bp"]).items():
                    values.append((fx_name, eff.channel, v))
            for fx_name, ch, v in values:
                fx = patch.find(fx_name)
                cdef = next((c for c in fx.profile.channels if c.name == ch), None)
                if cdef is None:
                    continue
                factor = self._factor(fx, cdef, level, cue.dimmer)
                for dmx_ch, dv in fx.channel_values({ch: round(v * factor)}).items():
                    layer.set(fx.universe, dmx_ch, dv)

    @staticmethod
    def _factor(fx, cdef, level: float, dimmer: float) -> float:
        """Fade e modificatore dimmer agiscono solo su intensità/colore; pan, tilt, gobo ecc. restano interi."""
        if not cdef.kind:
            return 1.0
        f = level
        has_dim = fx.profile.channel_of_kind("intensity") is not None
        if (cdef.kind == "intensity") or (not has_dim and cdef.kind in
                                          ("red", "green", "blue", "white", "amber", "uv")):
            f *= dimmer
        return f

    # --- cuelist ---
    def go(self, cl: CueList, page_priority: int = 0) -> bool:
        """Passa allo step successivo non saltato; False se la lista è finita (senza loop)."""
        with self.engine.mixer.lock:
            st = self._cl.get(cl.name)
            i = (st["i"] if st else -1)
            nxt = self._next_index(cl, i)
            if nxt is None:
                self._stop_cl(cl)
                return False
            self._enter(cl, nxt, page_priority)
            return True

    def goto(self, cl: CueList, number: int, page_priority: int = 0) -> None:
        """Salta allo step `number` (1-based), anche se marcato skip."""
        with self.engine.mixer.lock:
            if not 1 <= number <= len(cl.steps):
                raise IndexError(f"step {number} inesistente")
            self._enter(cl, number - 1, page_priority)

    def stop_cuelist(self, cl: CueList) -> None:
        with self.engine.mixer.lock:
            self._stop_cl(cl)

    def _next_index(self, cl: CueList, i: int) -> int | None:
        n = len(cl.steps)
        for k in range(1, n + 1):
            j = i + k
            if j >= n and not cl.loop:
                return None
            j %= n
            if not cl.steps[j].skip:
                return j
        return None

    def _enter(self, cl: CueList, idx: int, page_priority: int) -> None:
        cues = {c.name: c for c in self.engine.project.cues}
        step = cl.steps[idx]
        base = cues.get(step.cue)
        if base is None:
            raise KeyError(f"cue non trovato: {step.cue}")
        prev = self._cl.get(cl.name)
        if prev and prev["cue"] != step.cue:
            old = self.active.get(prev["cue"])
            if old:
                self.release(old["cue"], fade=step.fade, curve=step.curve)
        live = replace(base, fade_in=step.fade, fade_out=step.fade, curve=step.curve,
                       toggle=False, priority=cl.priority)
        if not (prev and prev["cue"] == step.cue and step.cue in self.active
                and not self.active[step.cue]["releasing"]):   # stesso cue: continuità, niente riavvio
            self.active.pop(step.cue, None)
            self._begin(live, page_priority)
        self._cl[cl.name] = {"i": idx, "cue": step.cue, "t": self._now(), "pp": page_priority}

    def _stop_cl(self, cl: CueList) -> None:
        st = self._cl.pop(cl.name, None)
        if st and st["cue"] in self.active:
            self.release(self.active[st["cue"]]["cue"])

    def _tick_cuelists(self) -> None:
        now = self._now()
        for cl in self._cl_defs():
            st = self._cl.get(cl.name)
            if not st:
                continue
            step = cl.steps[st["i"]]
            if step.hold is not None and now - st["t"] >= step.fade + step.hold:
                nxt = self._next_index(cl, st["i"])
                if nxt is None:
                    self._stop_cl(cl)
                else:
                    self._enter(cl, nxt, st["pp"])

    def _cl_defs(self) -> list[CueList]:
        return [p.cuelist for p in self.engine.project.pages if p.cuelist]

    def current_step(self, cl: CueList) -> int | None:
        st = self._cl.get(cl.name)
        return st["i"] + 1 if st else None
