"""Log del workspace (Workspace Status → Logs, manuale 4.1): trigger dei cue, MIDI in ingresso, OSC in ingresso e in uscita.

Ogni categoria si registra solo se abilitata in `workspace.settings["log_enabled"]` (salvato con il workspace)."""
from __future__ import annotations

import collections
import datetime

CATEGORIES = {"trigger": "Trigger dei cue", "midi_in": "MIDI in ingresso", "osc_in": "OSC in ingresso",
              "osc_out": "OSC in uscita"}
MAX_ENTRIES = 5000


class WorkspaceLogs:
    def __init__(self, workspace):
        self.workspace = workspace
        self.entries: collections.deque = collections.deque(maxlen=MAX_ENTRIES)

    def enabled(self, category: str) -> bool:
        return self.workspace.settings.get("log_enabled", {}).get(category, False) == True

    def set_enabled(self, category: str, value: bool) -> None:
        if category not in CATEGORIES:
            raise ValueError("categoria di log sconosciuta: " + category)
        self.workspace.settings.setdefault("log_enabled", {})[category] = value == True
        self.workspace.modified = True

    def add(self, category: str, text: str) -> None:
        if self.enabled(category) == False:
            return
        self.entries.append((datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], category, text))

    def lines(self, categories: list | None = None, filter_text: str = "") -> list[str]:
        needle = filter_text.lower()
        result = []
        for stamp, category, text in self.entries:
            if categories is not None and category not in categories:
                continue
            line = "%s [%s] %s" % (stamp, category, text)
            if needle == "" or needle in line.lower():
                result.append(line)
        return result

    def clear(self) -> None:
        self.entries.clear()


def format_arguments(arguments: list) -> str:
    return " ".join(str(item) for item in arguments)
