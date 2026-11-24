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


def export_palettes(palettes: list, path: str, names: list[str] | None = None) -> int:
    import json
    sel = [p for p in palettes if names is None or p.name in names]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"palettes": [{"name": p.name, "group": p.group,
                                 "presets": [{"name": x.name, "values": x.values} for x in p.presets]} for p in sel]}, fh, indent=2)
    return len(sel)


def import_palettes(palettes: list, path: str) -> int:
    """Importa; se una palette con lo stesso nome esiste, i preset nuovi vengono aggiunti (nomi doppi rinominati)."""
    import json
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    n = 0
    for d in doc["palettes"]:
        pal = next((p for p in palettes if p.name == d["name"]), None)
        if pal is None:
            pal = Palette(d["name"], [], d.get("group", "")); palettes.append(pal)
        for x in d["presets"]:
            name, k = x["name"], 2
            while any(y.name == name for y in pal.presets):
                name = f"{x['name']} {k}"; k += 1
            pal.presets.append(Preset(name, x["values"])); n += 1
    return n
