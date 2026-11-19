"""Live: cue con preset ed effetti, fade e priorità."""
from __future__ import annotations

from dataclasses import dataclass, field

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


class LivePlayer:
    """Gestisce i cue attivi; `update` scrive nei layer del mixer."""

    def __init__(self, engine, now):
        self.engine = engine
        self._now = now
        self.active: dict[str, dict] = {}   # nome cue -> stato
        self._layers: dict[int, object] = {}

    def trigger(self, cue: LiveCue) -> None:
        with self.engine.mixer.lock:
            self._trigger(cue)

    def _trigger(self, cue: LiveCue) -> None:
        st = self.active.get(cue.name)
        if st and cue.toggle and not st["releasing"]:
            return self.release(cue)
        self.active[cue.name] = {"cue": cue, "t0": self._now(), "releasing": False, "t1": 0.0}

    def release(self, cue: LiveCue) -> None:
        st = self.active.get(cue.name)
        if st and not st["releasing"]:
            st.update(releasing=True, t1=self._now())

    def _level(self, st) -> float:
        cue, now = st["cue"], self._now()
        f = CURVES[cue.curve]
        if st["releasing"]:
            if cue.fade_out <= 0:
                return 0.0
            return f(max(0.0, 1 - (now - st["t1"]) / cue.fade_out))
        if cue.fade_in <= 0:
            return 1.0
        return f(min(1.0, (now - st["t0"]) / cue.fade_in))

    def update(self) -> None:
        with self.engine.mixer.lock:
            self._update()

    def _update(self) -> None:
        """Ricalcola i layer del mixer da zero in base ai cue attivi."""
        for layer in self._layers.values():
            layer.clear()
        beats = self.engine.beat.beats()
        patch = self.engine.project.patch
        for name in list(self.active):
            st = self.active[name]
            level = self._level(st)
            if st["releasing"] and level <= 0:
                del self.active[name]
                continue
            cue = st["cue"]
            layer = self._layers.get(cue.priority)
            if layer is None:
                layer = self._layers[cue.priority] = self.engine.mixer.add_layer(cue.priority)
            values: list[tuple[str, str, float]] = []
            if cue.preset:
                for fx_name in cue.fixtures:
                    for ch, v in cue.preset.values.items():
                        values.append((fx_name, ch, v))
            for eff in cue.effects:
                for fx_name, v in eff.evaluate(cue.fixtures, beats).items():
                    values.append((fx_name, eff.channel, v))
            for fx_name, ch, v in values:
                fx = patch.find(fx_name)
                if ch not in {c.name for c in fx.profile.channels}:
                    continue
                for dmx_ch, dv in fx.channel_values({ch: round(v * level)}).items():
                    layer.set(fx.universe, dmx_ch, dv)
