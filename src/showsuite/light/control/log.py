"""Registro dei messaggi di controllo esterno (External Control Log)."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class LogEntry:
    time: float
    source: str        # "dmx" | "midi" | "osc"
    endpoint: str
    direction: str     # "in" | "out"
    message: str
    comment: str
    status: str        # "ok" | "learn" | "invalid" | "info"


class ControlLog:
    def __init__(self, maxlen: int = 500):
        self.entries: deque[LogEntry] = deque(maxlen=maxlen)
        self.paused = False
        self._lock = threading.Lock()

    def add(self, source: str, endpoint: str, message: str, comment: str = "", status: str = "ok",
            direction: str = "in") -> None:
        if self.paused:
            return
        with self._lock:
            self.entries.append(LogEntry(time.time(), source, endpoint, direction, message, comment, status))

    def snapshot(self, source: str | None = None) -> list[LogEntry]:
        with self._lock:
            return [e for e in self.entries if source in (None, e.source)]

    def clear(self) -> None:
        with self._lock:
            self.entries.clear()
