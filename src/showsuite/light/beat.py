"""Beat clock con tap tempo. Il tempo è iniettabile per i test."""
from __future__ import annotations

import time


class BeatClock:
    def __init__(self, bpm: float = 120.0, now=time.monotonic):
        self._now = now
        self.bpm = bpm
        self._origin = now()       # istante in cui beats == _origin_beats
        self._origin_beats = 0.0
        self._taps: list[float] = []

    def beats(self) -> float:
        return self._origin_beats + (self._now() - self._origin) * self.bpm / 60.0

    def set_bpm(self, bpm: float) -> None:
        if not 20 <= bpm <= 400:
            raise ValueError("BPM fuori range (20-400)")
        self._origin_beats = self.beats()   # niente salti di fase
        self._origin = self._now()
        self.bpm = bpm

    def tap(self) -> None:
        t = self._now()
        if self._taps and t - self._taps[-1] > 2.0:   # pausa lunga: ricomincia
            self._taps.clear()
        self._taps.append(t)
        self._taps = self._taps[-8:]
        if len(self._taps) >= 2:
            avg = (self._taps[-1] - self._taps[0]) / (len(self._taps) - 1)
            self.set_bpm(min(400, max(20, 60.0 / avg)))
        # allinea il battere al tap
        self._origin_beats = round(self.beats())
        self._origin = t
