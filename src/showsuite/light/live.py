"""Live: cue con preset ed effetti, fade e priorità."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .dmx.mixer import Mixer
from .colorfx import ColorEffect
from .patfx import PatternEffect
from .effects import Effect
from .posfx import PositionEffect
from .preset import Preset

CURVES = {
    "linear": lambda x: x,
    "ease_in": lambda x: x * x,
    "ease_out": lambda x: 1 - (1 - x) ** 2,
    "s_curve": lambda x: x * x * (3 - 2 * x),
    "custom": lambda x: x,      # sostituita da curve_fn(cue) quando il cue ha punti propri
}


def interp_curve(points, x: float) -> float:
    """Interpolazione lineare tra i punti (x, y); estremi (0,0) e (1,1) impliciti."""
    pts = sorted([(0.0, 0.0), *[(float(a), float(b)) for a, b in points], (1.0, 1.0)])
    x = max(0.0, min(1.0, x))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 if x1 == x0 else max(0.0, min(1.0, y0 + (y1 - y0) * (x - x0) / (x1 - x0)))
    return 1.0


def curve_fn(cue, name: str | None = None):
    name = name or cue.curve
    if name == "custom" and cue.curve_points:
        return lambda x: interp_curve(cue.curve_points, x)
    return CURVES[name]


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
    # Effetti evoluti: figure di posizione e colori (durata in secondi, scalata dal BPM di riferimento 120)
    position_fx: PositionEffect | None = None
    color_fx: ColorEffect | None = None
    pattern_fx: PatternEffect | None = None
    overlays: list = field(default_factory=list)   # effetti sovrapposti (Position/Color/PatternEffect): colori in screen, posizioni sommate
    beat_mult: float = 1.0      # moltiplicatore di beat (x0.25 … x4), si compone con speed
    time_offset: float = 0.0    # offset di fase in battute applicato a sequenze ed effetti
    hue_shift: float = 0.0      # rotazione della tonalità in gradi (-180…180) su tutti i colori del cue
    mods: dict = field(default_factory=dict)   # altri modificatori: fade_time, color_temp, green_sat, xfade, pan, tilt, focus, zoom, iris, frost, fog
    curve_points: list = field(default_factory=list)   # curva di fade personalizzata: punti (x, y) in 0-1, usata se curve == "custom"
    no_trigger: bool = False    # "Exclude from Live Triggers"


PAGE_PRIORITY_STEP = 100   # priorità effettiva = pagina * 100 + priorità del cue (0-99)


@dataclass
class CueListStep:
    cue: str
    hold: float | None = None   # None = manuale (aspetta GO); altrimenti secondi dopo il fade
    fade: float = 0.0
    curve: str = "linear"
    skip: bool = False
    also: list = field(default_factory=list)   # cue group: altri cue avviati insieme in questo step


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
    frame: int = 0              # indice della cornice nella pagina
    kind: str = "button"        # "button" | "fader" (fader verticale) | "text" (etichetta, nessun cue)
    group: str = ""             # stesso gruppo = pulsanti "attached": uno solo attivo, con crossfade
    startup: bool = False       # "Activate at startup": attivato all'apertura del progetto


def duplicate_button(project, page, btn):
    """Duplica pulsante e relativo cue (nome 'X copia', 'X copia 2'…); ritorna il nuovo LiveButton."""
    import copy
    new = copy.deepcopy(btn)
    if btn.kind != "text":
        src = next((c for c in project.cues if c.name == btn.cue), None)
        if src:
            names = {c.name for c in project.cues}
            n, name = 1, f"{src.name} copia"
            while name in names:
                n += 1; name = f"{src.name} copia {n}"
            c2 = copy.deepcopy(src); c2.name = name; project.cues.append(c2); new.cue = name
            new.group = ""
    page.buttons.insert(page.buttons.index(btn) + 1, new)
    return new


def paste_button(project, src_page, btn, dst_page, frame: int = 0):
    """Copia `btn` (con il suo cue) in un'altra pagina: ritorna il nuovo pulsante."""
    import copy
    tmp = LivePage("_tmp", [btn])
    new = duplicate_button(project, tmp, btn)
    tmp.buttons.remove(btn)          # duplicate_button l'ha messo accanto all'originale nella pagina temporanea
    new.frame = frame
    dst_page.buttons.append(new)
    return new


@dataclass
class LivePage:
    name: str
    buttons: list[LiveButton] = field(default_factory=list)
    priority: int = 0           # 0-99: tra pagine vince la più alta
    fade_time: float = 0.0      # secondi, cambio pagina
    columns: int = 6
    cuelist: CueList | None = None   # una cuelist per pagina
    frames: list[str] = field(default_factory=lambda: [""])   # titoli delle cornici


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

    def trigger_exclusive(self, cue: LiveCue, others: list[LiveCue], page_priority: int = 0) -> None:
        """Pulsanti "attached": spegne gli altri del gruppo (con il loro fade-out) e accende questo."""
        with self.engine.mixer.lock:
            for o in others:
                if o.name != cue.name:
                    self.release(o)
            st = self.active.get(cue.name)
            if st and not st["releasing"]:
                self.release(cue)        # secondo clic sul pulsante già attivo: lo spegne
            else:
                self.active.pop(cue.name, None)
                self._begin(cue, page_priority)

    def set_fader(self, cue: LiveCue, value: float, page_priority: int = 0) -> None:
        """Fader: livello 0-1 del cue. A 0 il cue si spegne, sopra 0 si accende se serve."""
        with self.engine.mixer.lock:
            value = max(0.0, min(1.0, value))
            st = self.active.get(cue.name)
            if value <= 0:
                if st:
                    del self.active[cue.name]
                return
            if not st or st["releasing"]:
                self.active.pop(cue.name, None)
                self._begin(cue, page_priority)
                st = self.active[cue.name]
            st["fader"] = value

    def apply_startup(self) -> int:
        """Attiva i cue dei pulsanti con 'Activate at startup' (non per le cuelist)."""
        cues = {c.name: c for c in self.engine.project.cues}; n = 0
        for pg in self.engine.project.pages:
            for b in pg.buttons:
                if b.startup and b.kind == "button" and b.cue in cues and b.cue not in self.active:
                    self.start(cues[b.cue], pg.priority); n += 1
        return n

    def snapshot_state(self) -> dict:
        """Stato da ricordare alla chiusura: cue attivi e Grand Master."""
        return {"active": [n for n, s in self.active.items() if not s["releasing"]],
                "grand_master": self.engine.grand_master}

    def restore_state(self, st: dict) -> None:
        cues = {c.name: c for c in self.engine.project.cues}
        pri = {b.cue: pg.priority for pg in self.engine.project.pages for b in pg.buttons}
        for n in st.get("active", []):
            if n in cues and n not in self.active:
                self.start(cues[n], pri.get(n, 0))
        self.engine.grand_master = float(st.get("grand_master", 1.0))

    def _shift_hue(self, values: list, degrees: float) -> list:
        """Ruota la tonalità dei fixture RGB presenti in `values` (l'ultimo valore per canale vince)."""
        import colorsys
        patch = self.engine.project.patch
        last: dict[tuple[str, str], float] = {}
        for f, c, v in values:
            last[(f, c)] = v
        out = [(f, c, v) for f, c, v in values]
        for f in {f for f, _ in last}:
            prof = patch.find(f).profile
            chans = [prof.channel_of_kind(k) for k in ("red", "green", "blue")]
            if not all(chans) or not all((f, c.name) in last for c in chans):
                continue
            r, g, b = (last[(f, c.name)] / 255 for c in chans)
            h, sat, val = colorsys.rgb_to_hsv(r, g, b)
            r2, g2, b2 = colorsys.hsv_to_rgb((h + degrees / 360) % 1.0, sat, val)
            for c, v in zip(chans, (r2, g2, b2)):
                out.append((f, c.name, round(v * 255)))
        return out

    def crossfade(self, a: LiveCue, b: LiveCue, x: float, page_priority: int = 0) -> None:
        """Crossfade manuale: x=0 solo A, x=1 solo B, in mezzo entrambi proporzionali."""
        x = max(0.0, min(1.0, x))
        self.set_fader(a, 1.0 - x, page_priority)
        self.set_fader(b, x, page_priority)

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
            fo = (cue.fade_out if fo is None else fo) * cue.mods.get("fade_time", 1.0)
            f = curve_fn(cue, st.get("curve_o"))
            if fo <= 0:
                return 0.0
            return f(max(0.0, 1 - (now - st["t1"]) / fo)) * st.get("fader", 1.0)
        f = curve_fn(cue)
        fi = cue.fade_in * cue.mods.get("fade_time", 1.0)
        if fi <= 0:
            return 1.0 * st.get("fader", 1.0)
        return f(min(1.0, (now - st["t0"]) / fi)) * st.get("fader", 1.0)

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
            st["bp"] += (beats - st["bl"]) * st["cue"].speed * st["cue"].beat_mult   # la velocità cambia senza salti di fase
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
            bp = st["bp"] + cue.time_offset          # fase usata da sequenze ed effetti (con offset)
            if cue.preset:
                for fx_name in cue.fixtures:
                    for ch, v in cue.preset.values.items():
                        values.append((fx_name, ch, v))
            if cue.steps:
                for fx_name in cue.fixtures:
                    for ch, v in self._step_values(cue, st, bp).items():
                        values.append((fx_name, ch, v))
            for eff in cue.effects:
                for fx_name, v in eff.evaluate(cue.fixtures, bp).items():
                    values.append((fx_name, eff.channel, v))
            t = bp * 0.5      # secondi equivalenti a 120 BPM; il BPM reale accelera via beat clock
            colors: dict[str, tuple] = {}     # colori combinati con blend "screen" (come gli overlay di Lightkey)
            moves: dict[str, tuple] = {}      # posizioni sommate
            def add_color(fx_name, rgb):
                old = colors.get(fx_name)
                colors[fx_name] = tuple(rgb) if old is None else tuple(
                    round(255 - (255 - a_) * (255 - b_) / 255) for a_, b_ in zip(old, rgb))
            for eff in [cue.pattern_fx, cue.color_fx, cue.position_fx, *cue.overlays]:
                if eff is None:
                    continue
                if isinstance(eff, PatternEffect):
                    for fx_name, rgb in eff.evaluate([patch.find(n) for n in cue.fixtures], bp * 0.5, bp).items():
                        add_color(fx_name, rgb)
                elif isinstance(eff, ColorEffect):
                    for fx_name, rgb in eff.evaluate(cue.fixtures, t).items():
                        add_color(fx_name, rgb)
                elif isinstance(eff, PositionEffect):
                    for fx_name, (x, y) in eff.evaluate(cue.fixtures, t).items():
                        ox, oy = moves.get(fx_name, (0.0, 0.0)); moves[fx_name] = (max(-1, min(1, ox + x)), max(-1, min(1, oy + y)))
            for fx_name, rgb in colors.items():
                prof = patch.find(fx_name).profile
                chans = [prof.channel_of_kind(k) for k in ("red", "green", "blue")]
                if all(chans):
                    values.extend((fx_name, c.name, v) for c, v in zip(chans, rgb))
                elif prof.channel_of_kind("intensity"):
                    values.append((fx_name, prof.channel_of_kind("intensity").name, max(rgb)))
            for fx_name, (x, y) in moves.items():
                prof = patch.find(fx_name).profile
                for kind, v in (("pan", x), ("tilt", y)):
                    c = prof.channel_of_kind(kind)
                    if c:
                        values.append((fx_name, c.name, round((0.5 + v / 2) * (65535 if c.fine else 255))))
            if cue.hue_shift:
                values = self._shift_hue(values, cue.hue_shift)
            if cue.mods:
                values = self._apply_mods(values, cue.mods)
            for fx_name, ch, v in values:
                fx = patch.find(fx_name)
                cdef = next((c for c in fx.profile.channels if c.name == ch), None)
                if cdef is None:
                    continue
                factor = self._factor(fx, cdef, level, cue.dimmer)
                for dmx_ch, dv in fx.channel_values({ch: round(v * factor)}).items():
                    layer.set(fx.universe, dmx_ch, dv)

    def _apply_mods(self, values: list, m: dict) -> list:
        """Modificatori del manuale: pan/tilt sommati (±180°), focus/zoom/iris/frost/fog moltiplicati,
        temperatura colore (±5000 K), green saturation (±100 %), xfade to color (moltiplicato)."""
        patch = self.engine.project.patch
        out = []
        for f, c, v in values:
            try:
                prof = patch.find(f).profile
            except KeyError:
                out.append((f, c, v)); continue
            cd = next((x for x in prof.channels if x.name == c), None)
            k = cd.kind if cd else ""
            top = 65535 if (cd and cd.fine) else 255
            if k in ("pan", "tilt") and m.get(k):
                span = 540.0     # escursione standard presunta (gradi) quando il profilo non ne indica una
                v = max(0, min(top, v + m[k] / span * top))
            elif k in ("focus", "zoom", "iris", "frost", "fog") and k in m:
                v = max(0, min(top, v * m[k]))
            out.append((f, c, v))
        ct, gs, xf = m.get("color_temp", 0.0), m.get("green_sat", 0.0), m.get("xfade")
        if ct or gs or xf is not None:
            last = {(f, c): v for f, c, v in out}
            for f in {f for f, _ in last}:
                prof = patch.find(f).profile
                ch = [prof.channel_of_kind(k) for k in ("red", "green", "blue")]
                if not all(ch) or not all((f, x.name) in last for x in ch):
                    continue
                r, g, b = (last[(f, x.name)] for x in ch)
                t = ct / 5000.0          # >0 caldo (arancio), <0 freddo (blu)
                r, b = r * (1 + 0.3 * t), b * (1 - 0.3 * t)
                g = g * (1 - gs / 100.0 * 0.5) if gs else g
                if xf is not None:       # moltiplica la distanza dal bianco
                    mx = max(r, g, b)
                    r, g, b = (mx - (mx - x) * xf for x in (r, g, b))
                for x, v in zip(ch, (r, g, b)):
                    out.append((f, x.name, round(max(0, min(255, v)))))
        return out

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
        names = [step.cue] + [n for n in step.also if n != step.cue]
        missing = [n for n in names if n not in cues]
        if missing:
            raise KeyError(f"cue non trovato: {missing[0]}")
        prev = self._cl.get(cl.name)
        for old_name in (prev["names"] if prev else []):
            if old_name not in names and old_name in self.active:
                self.release(self.active[old_name]["cue"], fade=step.fade, curve=step.curve)
        for n in names:
            live = replace(cues[n], fade_in=step.fade, fade_out=step.fade, curve=step.curve,
                           toggle=False, priority=cl.priority)
            if not (prev and n in prev["names"] and n in self.active and not self.active[n]["releasing"]):
                self.active.pop(n, None)       # stesso cue di prima: continuità, niente riavvio
                self._begin(live, page_priority)
        self._cl[cl.name] = {"i": idx, "cue": step.cue, "names": names, "t": self._now(), "pp": page_priority}

    def _stop_cl(self, cl: CueList) -> None:
        st = self._cl.pop(cl.name, None)
        for n in (st["names"] if st else []):
            if n in self.active:
                self.release(self.active[n]["cue"])

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
