"""Preset e Palette."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Preset:
    """Insieme di valori per nome canale, applicabile a qualunque fixture che li possieda."""
    name: str
    values: dict[str, int] = field(default_factory=dict)


@dataclass
class Palette:
    name: str
    presets: list[Preset] = field(default_factory=list)
    group: str = ""          # cartella (gruppo di fixture) a cui appartiene; vuoto = tutti

    def get(self, name: str) -> Preset:
        for p in self.presets:
            if p.name == name:
                return p
        raise KeyError(name)
