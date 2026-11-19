"""LightEngine: progetto + mixer + programmer + uscite. Nessuna dipendenza dalla UI."""
from __future__ import annotations

import time

from .beat import BeatClock
from .dmx import Mixer, OutputManager
from .live import LivePlayer
from .fixtures import FixtureInstance
from .project import OutputConfig, Project


class LightEngine:
    def __init__(self, project: Project | None = None, now=time.monotonic):
        self.project = project or Project()
        self.mixer = Mixer()
        self.programmer = self.mixer.add_layer(100)  # valori impostati a mano
        self.values: dict[str, dict[str, int]] = {}  # fixture -> {canale: valore}
        self.output: OutputManager | None = None
        self.beat = BeatClock(120.0, now)
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

    def fixture_color(self, fx: FixtureInstance) -> tuple[int, int, int]:
        """Colore indicativo per il Preview, dall'uscita reale (programmer + cue)."""
        data = self.mixer.render(fx.universe)
        prof = fx.profile

        def val(name):
            return data[fx.address - 1 + prof.offset_of(name)]
        names = {c.name for c in prof.channels}
        dim = val("Dimmer") / 255 if "Dimmer" in names else 1.0
        if {"Red", "Green", "Blue"} <= names:
            r, g, b = val("Red"), val("Green"), val("Blue")
        else:
            r = g = b = 255
        return int(r * dim), int(g * dim), int(b * dim)

    # --- uscite ---
    def start_output(self) -> None:
        self.stop_output()
        self.output = OutputManager(self.mixer, pre_render=self.live.update)
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
