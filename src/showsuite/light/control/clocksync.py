"""Sincronizzazione del beat da MIDI clock esterno (24 impulsi per quarto)."""
from __future__ import annotations

import time
from collections import deque

PPQN = 24


class MidiClockSync:
    """Alimentata da on_clock/on_start/on_stop/on_continue; regola il BeatClock dell'engine."""

    def __init__(self, beat, now=time.monotonic, min_change_bpm: float = 0.3):
        self.beat = beat
        self._now = now
        self.min_change = min_change_bpm
        self.enabled = True
        self._times: deque[float] = deque(maxlen=PPQN * 2 + 1)
        self._ticks = 0           # impulsi dall'ultimo START
        self.running = False
        self.locked_phase = False  # True dopo uno START: la fase segue la griglia del master

    def on_start(self) -> None:
        self._ticks = 0
        self.running = True
        self.locked_phase = True
        if self.enabled:
            self.beat.align(0.0)

    def on_continue(self) -> None:
        self.running = True

    def on_stop(self) -> None:
        self.running = False

    def on_clock(self) -> None:
        if not self.enabled:
            return
        t = self._now()
        if self._times and t - self._times[-1] > 1.0:   # il master si è fermato e riparte
            self._times.clear()
        self._times.append(t)
        if self.running or not self.locked_phase:
            if self.running:
                self._ticks += 1
        if len(self._times) > PPQN:
            span = self._times[-1] - self._times[0]
            n = len(self._times) - 1
            if span > 0:
                bpm = 60.0 * n / (span * PPQN)
                if 20 <= bpm <= 400 and abs(bpm - self.beat.bpm) >= self.min_change:
                    self.beat.set_bpm(bpm)
        if self.running and self.locked_phase and self._ticks % PPQN == 0:
            self.beat.align(self._ticks / PPQN)   # corregge la deriva sul battere
