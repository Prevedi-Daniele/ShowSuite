"""Elenco dei progetti recenti (JSON nella cartella di configurazione dell'utente)."""
from __future__ import annotations

import json
import os
from pathlib import Path

MAX_RECENT = 10


def _file() -> Path:
    base = os.environ.get("SHOWSUITE_CONFIG") or os.path.join(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config", "showsuite")
    return Path(base) / "recents.json"


def load() -> list[str]:
    try:
        return [p for p in json.loads(_file().read_text()) if isinstance(p, str)]
    except Exception:
        return []


def add(path: str) -> list[str]:
    items = [path] + [p for p in load() if p != path]
    items = items[:MAX_RECENT]
    try:
        _file().parent.mkdir(parents=True, exist_ok=True); _file().write_text(json.dumps(items))
    except OSError:
        pass
    return items


def clear() -> None:
    try:
        _file().unlink()
    except OSError:
        pass
