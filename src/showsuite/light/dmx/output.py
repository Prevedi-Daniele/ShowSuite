"""OutputManager: instrada ogni universo verso N driver a frequenza fissa."""
from __future__ import annotations

import threading
import time

from .drivers.base import OutputDriver
from .mixer import Mixer


class OutputManager:
    def __init__(self, mixer: Mixer, rate_hz: float = 44.0, pre_render=None, post_render=None, render=None):
        self.mixer = mixer
        self.post_render = post_render  # (universo, dati) -> dati: master, blackout, freeze
        self.render = render or mixer.render  # (universo) -> 512 byte; l'engine lo usa per il blind
        self.pre_render = pre_render  # chiamato prima di ogni frame (cue, effetti)
        self.rate_hz = rate_hz
        self.routes: list[tuple[int, OutputDriver]] = []  # (universo, driver)
        self.errors: list[tuple[OutputDriver, Exception]] = []
        self._opened: set[int] = set()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def route(self, universe: int, driver: OutputDriver) -> None:
        """Nessun limite: stesso universo su più driver, più driver diversi."""
        self.routes.append((universe, driver))

    def tick(self) -> None:
        """Un frame: render di ogni universo instradato e invio."""
        if self.pre_render:
            self.pre_render()
        frames: dict[int, bytes] = {}
        for universe, driver in self.routes:
            if id(driver) not in self._opened:
                try:
                    driver.open()
                    self._opened.add(id(driver))
                except Exception as e:  # un'interfaccia guasta non blocca le altre
                    self.errors.append((driver, e))
                    continue
            if universe not in frames:
                data = self.render(universe)
                frames[universe] = self.post_render(universe, data) if self.post_render else data
            data = frames[universe]
            try:
                driver.send(universe, data)
            except Exception as e:
                self.errors.append((driver, e))

    def start(self) -> None:
        if self._thread:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="dmx-output", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        period = 1.0 / self.rate_hz
        nxt = time.perf_counter()
        while not self._stop.is_set():
            self.tick()
            nxt += period
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            else:
                nxt = time.perf_counter()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        for _, d in self.routes:
            if id(d) in self._opened:
                try:
                    d.close()
                except Exception:
                    pass
        self._opened.clear()
