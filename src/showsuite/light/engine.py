"""LightEngine: progetto + mixer + programmer + uscite. Nessuna dipendenza dalla UI."""
from __future__ import annotations

import time

from .beat import BeatClock
from .dmx import Mixer, OutputManager
from .live import LivePlayer
from .fixtures import FixtureInstance, generic_dimmer, generic_rgb
from .project import OutputConfig, Project


class LightEngine:
    def __init__(self, project: Project | None = None, now=time.monotonic):
        self.project = project or Project()
        self.mixer = Mixer()
        self.programmer = self.mixer.add_layer(10**6)  # override: sopra a tutti i cue
        self.values: dict[str, dict[str, int]] = {}  # fixture -> {canale: valore}
        self.output: OutputManager | None = None
        self.beat = BeatClock(120.0, now)
        self.library: dict = {"Dimmer generico (1 ch)": generic_dimmer(), "RGB generico (3 ch)": generic_rgb()}
        try:
            from .userlib import load_all
            for p in load_all():
                self.library[f"{p.manufacturer} {p.model} — {p.mode} ({p.footprint} ch)".strip()] = p
        except Exception:
            pass
        self._highlight = self.mixer.add_layer(10**7)   # sopra a tutto, solo per riconoscere i fixture
        self.blind = False   # se attivo il programmer non va in uscita (resta nel Preview)
        self.grand_master = 1.0
        self.blackout = False
        self.freeze = False
        self._frozen: dict[int, bytes] = {}
        self.live = LivePlayer(self, now)

    # --- valori ---
    def set_value(self, fixture: str, channel: str, value: int) -> None:
        fx = self.project.patch.find(fixture)
        self.values.setdefault(fixture, {})[channel] = value
        for ch, v in fx.channel_values({channel: value}).items():
            self.programmer.set(fx.universe, ch, v)

    def get_value(self, fixture: str, channel: str) -> int:
        fx = self.project.patch.find(fixture)
        if channel in self.values.get(fixture, {}):
            return self.values[fixture][channel]
        return next(c.default for c in fx.profile.channels if c.name == channel)

    def clear_programmer(self) -> None:
        self.programmer.clear()
        self.values.clear()

    def release_programmer(self, fixture: str) -> None:
        """Toglie dal programmer i valori di un fixture (es. dopo averli registrati in un cue)."""
        fx = self.project.patch.find(fixture)
        for ch in range(fx.address, fx.end_address + 1):
            self.programmer.release(fx.universe, ch)
        self.values.pop(fixture, None)

    def remove_fixture(self, fixture: str) -> None:
        fx = self.project.patch.find(fixture)
        for ch in range(fx.address, fx.end_address + 1):
            self.programmer.release(fx.universe, ch)
        self.values.pop(fixture, None)
        self.project.patch.remove(fixture)
        for g in self.project.groups:
            g.fixtures = [n for n in g.fixtures if n != fixture]
        self.project.groups = [g for g in self.project.groups if g.fixtures]

    def fixture_color(self, fx: FixtureInstance) -> tuple[int, int, int]:
        """Colore indicativo per il Preview, dall'uscita reale (programmer + cue)."""
        data = self.mixer.render(fx.universe)
        prof = fx.profile

        def val(kind):
            c = prof.channel_of_kind(kind)
            return data[fx.address - 1 + prof.offset_of(c.name)] if c else None
        dim = val("intensity")
        dim = 1.0 if dim is None else dim / 255
        r, g, b = val("red"), val("green"), val("blue")
        if r is None and g is None and b is None:
            r = g = b = 255
        r, g, b = (r or 0), (g or 0), (b or 0)
        w = val("white") or 0
        r, g, b = min(255, r + w), min(255, g + w), min(255, b + w)
        return int(r * dim), int(g * dim), int(b * dim)

    def import_ofl(self, path: str) -> int:
        """Importa un file OFL nella libreria; restituisce quante modalità ha aggiunto."""
        from .fixtures.ofl import load_ofl
        profiles = load_ofl(path)
        for p in profiles:
            self.library[f"{p.manufacturer} {p.model} — {p.mode} ({p.footprint} ch)".strip()] = p
        return len(profiles)

    # --- master / blackout / freeze ---
    def _intensity_channels(self) -> dict[int, list[int]]:
        """universo -> canali DMX da scalare con il Grand Master (intensità, o colori se manca)."""
        out: dict[int, list[int]] = {}
        for fx in self.project.patch.fixtures:
            prof = fx.profile
            c = prof.channel_of_kind("intensity")
            kinds = [c] if c else [k for k in (prof.channel_of_kind(x) for x in
                                              ("red", "green", "blue", "white", "amber", "uv")) if k]
            for k in kinds:
                out.setdefault(fx.universe, []).append(fx.address + prof.offset_of(k.name))
        return out

    def set_highlight(self, names) -> None:
        """Accende al massimo i fixture indicati (Highlight Mode). Lista vuota = spegne."""
        self._highlight.clear()
        for n in names:
            try:
                fx = self.project.patch.find(n)
            except KeyError:
                continue
            for c in fx.profile.channels:
                if c.kind:   # intensità e colori
                    for ch, v in fx.channel_values({c.name: 65535 if c.fine else 255}).items():
                        self._highlight.set(fx.universe, ch, v)

    def render_output(self, universe: int) -> bytes:
        return self.mixer.render(universe, skip={self.programmer} if self.blind else ())

    def _apply_fixture_options(self, universe: int, buf: bytearray, gm: float) -> None:
        """Opzioni dei fixture sull'uscita: disabilitati a zero, offset pan/tilt, limiti dimmer, Grand Master."""
        for fx in self.project.patch.fixtures:
            if fx.universe != universe:
                continue
            prof = fx.profile
            a0 = fx.address - 1
            if fx.disabled:
                buf[a0:a0 + prof.footprint] = bytes(prof.footprint)
                continue
            for kind, off, rng in (("pan", fx.pan_offset, fx.pan_range), ("tilt", fx.tilt_offset, fx.tilt_range)):
                c = prof.channel_of_kind(kind)
                if c and off and rng:
                    i = a0 + prof.offset_of(c.name)
                    cur = (buf[i] << 8 | buf[i + 1]) if c.fine else buf[i] * 257
                    new = max(0, min(65535, round(cur + off / rng * 65535)))
                    if c.fine:
                        buf[i], buf[i + 1] = new >> 8, new & 0xFF
                    else:
                        buf[i] = round(new / 257)
            c = prof.channel_of_kind("intensity")
            kinds = [c] if c else [k for k in (prof.channel_of_kind(x) for x in ("red", "green", "blue", "white", "amber", "uv")) if k]
            lim = fx.dimmer_min != 0 or fx.dimmer_max != 255
            for k in kinds:
                i = a0 + prof.offset_of(k.name)
                v = buf[i]
                if lim and c:      # i limiti valgono solo per il canale dimmer vero e proprio
                    v = round(fx.dimmer_min + v / 255 * (fx.dimmer_max - fx.dimmer_min))
                if gm < 1.0 and not fx.ignore_master:
                    v = round(v * gm)
                buf[i] = v

    def _has_fixture_options(self) -> bool:
        return any(f.disabled or f.pan_offset or f.tilt_offset or f.dimmer_min != 0 or f.dimmer_max != 255 or f.ignore_master
                   for f in self.project.patch.fixtures)

    def process(self, universe: int, data: bytes) -> bytes:
        """Ultimo stadio prima delle uscite: freeze, opzioni fixture, grand master, blackout."""
        if self.freeze and universe in self._frozen:
            return self._frozen[universe]
        gm = 0.0 if self.blackout else self.grand_master
        if gm < 1.0 or self._has_fixture_options():
            buf = bytearray(data)
            self._apply_fixture_options(universe, buf, gm)
            data = bytes(buf)
        if self.freeze:
            self._frozen[universe] = data
        return data

    def set_freeze(self, on: bool) -> None:
        self._frozen = {}
        self.freeze = on   # il primo frame dopo l'attivazione viene mantenuto

    # --- uscite ---
    def start_output(self) -> None:
        self.stop_output()
        self.output = OutputManager(self.mixer, pre_render=self.live.update, post_render=self.process,
                                    render=self.render_output)
        for cfg in self.project.outputs:
            self.output.route(cfg.universe, cfg.build())
        self.output.start()

    def stop_output(self) -> None:
        if self.output:
            self.output.stop()
            self.output = None

    def output_errors(self) -> list[str]:
        if not self.output:
            return []
        return [f"{type(d).__name__}: {e}" for d, e in self.output.errors[-5:]]
