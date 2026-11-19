"""Progetto Light: file .showsuite-light = ZIP con project.json + profiles/."""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field

from .dmx.drivers import ArtNetDriver, OpenDmxDriver, OutputDriver, SacnDriver
from .fixtures import ChannelDef, FixtureInstance, FixtureProfile, Patch

SCHEMA_VERSION = 1
MAX_UNIVERSES = 16


@dataclass
class OutputConfig:
    type: str          # "artnet" | "sacn" | "opendmx"
    universe: int      # universo del progetto che esce da questa destinazione
    params: dict = field(default_factory=dict)  # host / port seriale / ...

    def build(self) -> OutputDriver:
        p = self.params
        if self.type == "artnet":
            return ArtNetDriver(p.get("host", "255.255.255.255"))
        if self.type == "sacn":
            return SacnDriver(p.get("unicast"), priority=p.get("priority", 100))
        if self.type == "opendmx":
            return OpenDmxDriver(p["port"], universe=self.universe)
        raise ValueError(f"tipo uscita sconosciuto: {self.type}")


@dataclass
class Project:
    name: str = "Senza titolo"
    patch: Patch = field(default_factory=Patch)
    outputs: list[OutputConfig] = field(default_factory=list)


def _profile_id(p: FixtureProfile) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", f"{p.manufacturer}_{p.model}_{p.mode}")


def _profile_to_dict(p: FixtureProfile) -> dict:
    return {"manufacturer": p.manufacturer, "model": p.model, "mode": p.mode,
            "channels": [{"name": c.name, "default": c.default, "fine": c.fine} for c in p.channels]}


def _profile_from_dict(d: dict) -> FixtureProfile:
    return FixtureProfile(d["manufacturer"], d["model"], d["mode"],
                          tuple(ChannelDef(c["name"], c.get("default", 0), c.get("fine", False))
                                for c in d["channels"]))


def save(project: Project, path: str) -> None:
    profiles = {}
    fixtures = []
    for f in project.patch.fixtures:
        pid = _profile_id(f.profile)
        profiles[pid] = f.profile
        fixtures.append({"name": f.name, "profile": pid, "universe": f.universe,
                         "address": f.address, "x": f.x, "y": f.y})
    doc = {"schema_version": SCHEMA_VERSION, "name": project.name, "fixtures": fixtures,
           "outputs": [{"type": o.type, "universe": o.universe, "params": o.params}
                       for o in project.outputs]}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(doc, indent=2, ensure_ascii=False))
        for pid, prof in profiles.items():
            z.writestr(f"profiles/{pid}.json", json.dumps(_profile_to_dict(prof), indent=2))


def load(path: str) -> Project:
    with zipfile.ZipFile(path) as z:
        doc = json.loads(z.read("project.json"))
        ver = doc.get("schema_version")
        if ver != SCHEMA_VERSION:
            raise ValueError(f"versione progetto non supportata: {ver}")
        profiles = {n.split("/")[-1][:-5]: _profile_from_dict(json.loads(z.read(n)))
                    for n in z.namelist() if n.startswith("profiles/") and n.endswith(".json")}
    proj = Project(name=doc["name"])
    for f in doc["fixtures"]:
        proj.patch.add(FixtureInstance(f["name"], profiles[f["profile"]], f["universe"],
                                       f["address"], f.get("x", 0.5), f.get("y", 0.5)))
    proj.outputs = [OutputConfig(o["type"], o["universe"], o.get("params", {}))
                    for o in doc["outputs"]]
    return proj
