"""Progetto Light: file .showsuite-light = ZIP con project.json + profiles/."""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field

from .dmx.drivers import ArtNetDriver, OpenDmxDriver, OutputDriver, SacnDriver
from .effects import Effect
from .fixtures import ChannelDef, FixtureInstance, FixtureProfile, Patch
from .control.dmxin import DmxMapping
from .control.midi import MidiMapping
from .live import CueList, CueListStep, LiveButton, LiveCue, LivePage
from .preset import Palette, Preset

SCHEMA_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)  # la v1 non ha palette/cue
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
    palettes: list[Palette] = field(default_factory=list)
    cues: list[LiveCue] = field(default_factory=list)
    pages: list[LivePage] = field(default_factory=list)
    midi_mappings: list[MidiMapping] = field(default_factory=list)
    osc_port: int = 21600
    dmx_mappings: list[DmxMapping] = field(default_factory=list)


def _cue_to_dict(c: LiveCue) -> dict:
    return {"name": c.name, "fixtures": c.fixtures, "fade_in": c.fade_in, "fade_out": c.fade_out,
            "curve": c.curve, "priority": c.priority, "toggle": c.toggle,
            "preset": ({"name": c.preset.name, "values": c.preset.values} if c.preset else None),
            "effects": [vars(e) for e in c.effects],
            "steps": [{"name": x.name, "values": x.values} for x in c.steps],
            "beats_per_step": c.beats_per_step, "crossfade": c.crossfade, "loop": c.loop,
            "speed": c.speed, "dimmer": c.dimmer}


def _cue_from_dict(d: dict) -> LiveCue:
    pr = d.get("preset")
    return LiveCue(d["name"], d["fixtures"], Preset(pr["name"], pr["values"]) if pr else None,
                   [Effect(**e) for e in d.get("effects", [])], d.get("fade_in", 0.0),
                   d.get("fade_out", 0.0), d.get("curve", "linear"), d.get("priority", 10),
                   d.get("toggle", True),
                   [Preset(x["name"], x["values"]) for x in d.get("steps", [])],
                   d.get("beats_per_step", 1.0), d.get("crossfade", 0.0), d.get("loop", True),
                   d.get("speed", 1.0), d.get("dimmer", 1.0))


def _profile_id(p: FixtureProfile) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", f"{p.manufacturer}_{p.model}_{p.mode}")


def _profile_to_dict(p: FixtureProfile) -> dict:
    return {"manufacturer": p.manufacturer, "model": p.model, "mode": p.mode,
            "channels": [{"name": c.name, "default": c.default, "fine": c.fine, "kind": c.kind,
                          "caps": [list(x) for x in c.caps]} for c in p.channels]}


def _profile_from_dict(d: dict) -> FixtureProfile:
    return FixtureProfile(d["manufacturer"], d["model"], d["mode"],
                          tuple(ChannelDef(c["name"], c.get("default", 0), c.get("fine", False), c.get("kind", ""),
                                      tuple(tuple(x) for x in c.get("caps", [])))
                                for c in d["channels"]))


def save(project: Project, path: str) -> None:
    profiles = {}
    fixtures = []
    for f in project.patch.fixtures:
        pid = _profile_id(f.profile)
        profiles[pid] = f.profile
        fixtures.append({"name": f.name, "profile": pid, "universe": f.universe,
                         "address": f.address, "x": f.x, "y": f.y, "rotation": f.rotation,
                         "beam_angle": f.beam_angle, "hide_beam": f.hide_beam})
    doc = {"schema_version": SCHEMA_VERSION, "name": project.name, "fixtures": fixtures,
           "outputs": [{"type": o.type, "universe": o.universe, "params": o.params}
                       for o in project.outputs],
           "palettes": [{"name": p.name, "presets": [{"name": x.name, "values": x.values}
                                                     for x in p.presets]} for p in project.palettes],
           "cues": [_cue_to_dict(c) for c in project.cues],
           "pages": [{"name": p.name, "priority": p.priority, "fade_time": p.fade_time,
                      "columns": p.columns, "buttons": [vars(b) for b in p.buttons],
                      "cuelist": ({"name": p.cuelist.name, "loop": p.cuelist.loop, "priority": p.cuelist.priority,
                                   "steps": [vars(x) for x in p.cuelist.steps]} if p.cuelist else None)}
                     for p in project.pages],
           "midi_mappings": [vars(m) for m in project.midi_mappings], "osc_port": project.osc_port,
           "dmx_mappings": [vars(m) for m in project.dmx_mappings]}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(doc, indent=2, ensure_ascii=False))
        for pid, prof in profiles.items():
            z.writestr(f"profiles/{pid}.json", json.dumps(_profile_to_dict(prof), indent=2))


def load(path: str) -> Project:
    with zipfile.ZipFile(path) as z:
        doc = json.loads(z.read("project.json"))
        ver = doc.get("schema_version")
        if ver not in SUPPORTED_VERSIONS:
            raise ValueError(f"versione progetto non supportata: {ver}")
        profiles = {n.split("/")[-1][:-5]: _profile_from_dict(json.loads(z.read(n)))
                    for n in z.namelist() if n.startswith("profiles/") and n.endswith(".json")}
    proj = Project(name=doc["name"])
    for f in doc["fixtures"]:
        proj.patch.add(FixtureInstance(f["name"], profiles[f["profile"]], f["universe"],
                                       f["address"], f.get("x", 0.5), f.get("y", 0.5),
                                       f.get("rotation", 0.0), f.get("beam_angle", 30.0),
                                       f.get("hide_beam", False)))
    proj.outputs = [OutputConfig(o["type"], o["universe"], o.get("params", {}))
                    for o in doc["outputs"]]
    proj.palettes = [Palette(p["name"], [Preset(x["name"], x["values"]) for x in p["presets"]])
                     for p in doc.get("palettes", [])]
    proj.cues = [_cue_from_dict(c) for c in doc.get("cues", [])]
    proj.pages = [LivePage(p["name"], [LiveButton(**b) for b in p.get("buttons", [])], p.get("priority", 0),
                           p.get("fade_time", 0.0), p.get("columns", 6),
                           (CueList(p["cuelist"]["name"], [CueListStep(**x) for x in p["cuelist"]["steps"]],
                                    p["cuelist"].get("loop", False), p["cuelist"].get("priority", 10))
                            if p.get("cuelist") else None)) for p in doc.get("pages", [])]
    if not proj.pages and proj.cues:   # progetti senza pagine: tutti i cue su una pagina
        proj.pages = [LivePage("Pagina 1", [LiveButton(c.name) for c in proj.cues])]
    proj.midi_mappings = [MidiMapping(**m) for m in doc.get("midi_mappings", [])]
    proj.osc_port = doc.get("osc_port", 21600)
    proj.dmx_mappings = [DmxMapping(**m) for m in doc.get("dmx_mappings", [])]
    return proj
