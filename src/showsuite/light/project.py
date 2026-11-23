"""Progetto Light: file .showsuite-light = ZIP con project.json + profiles/."""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field

from .dmx.drivers import ArtNetDriver, OpenDmxDriver, OutputDriver, SacnDriver
from .colorfx import ColorEffect
from .patfx import PatternEffect
from .effects import Effect
from .posfx import PositionEffect
from .fixtures import ChannelDef, FixtureInstance, FixtureProfile, Patch
from .control.dmxin import DmxMapping
from .control.midi import MidiMapping
from .stage import FixtureGroup, StageShape
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
    shapes: list[StageShape] = field(default_factory=list)   # tralicci, linee, testi del Preview
    groups: list[FixtureGroup] = field(default_factory=list)  # gruppi di fixture
    background: bytes | None = None                           # immagine di sfondo (PNG/JPG) incorporata


def _cue_to_dict(c: LiveCue) -> dict:
    return {"name": c.name, "fixtures": c.fixtures, "fade_in": c.fade_in, "fade_out": c.fade_out,
            "curve": c.curve, "priority": c.priority, "toggle": c.toggle,
            "preset": ({"name": c.preset.name, "values": c.preset.values} if c.preset else None),
            "effects": [vars(e) for e in c.effects],
            "steps": [{"name": x.name, "values": x.values} for x in c.steps],
            "beats_per_step": c.beats_per_step, "crossfade": c.crossfade, "loop": c.loop,
            "speed": c.speed, "dimmer": c.dimmer,
            "position_fx": vars(c.position_fx) if c.position_fx else None,
            "pattern_fx": ({**vars(c.pattern_fx), "samples": [list(x) for x in c.pattern_fx.samples]}
                           if c.pattern_fx else None),
            "color_fx": ({**vars(c.color_fx), "swatches": [list(x) for x in c.color_fx.swatches]}
                         if c.color_fx else None)}


def _cue_from_dict(d: dict) -> LiveCue:
    pr = d.get("preset")
    return LiveCue(d["name"], d["fixtures"], Preset(pr["name"], pr["values"]) if pr else None,
                   [Effect(**e) for e in d.get("effects", [])], d.get("fade_in", 0.0),
                   d.get("fade_out", 0.0), d.get("curve", "linear"), d.get("priority", 10),
                   d.get("toggle", True),
                   [Preset(x["name"], x["values"]) for x in d.get("steps", [])],
                   d.get("beats_per_step", 1.0), d.get("crossfade", 0.0), d.get("loop", True),
                   d.get("speed", 1.0), d.get("dimmer", 1.0),
                   PositionEffect(**d["position_fx"]) if d.get("position_fx") else None,
                   _color_fx(d["color_fx"]) if d.get("color_fx") else None,
                   _pattern_fx(d["pattern_fx"]) if d.get("pattern_fx") else None)


def _pattern_fx(d: dict) -> PatternEffect:
    d = dict(d); d["samples"] = [tuple(x) for x in d.get("samples", [])]
    return PatternEffect(**d)


def _color_fx(d: dict) -> ColorEffect:
    d = dict(d)
    d["swatches"] = [tuple(x) for x in d.get("swatches", [])]
    for k in ("hue", "saturation", "brightness"):
        d[k] = [tuple(x) for x in d.get(k, [])]
    return ColorEffect(**d)


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


def _w(z: zipfile.ZipFile, name: str, data) -> None:
    """Scrive con data fissa: due salvataggi identici producono byte identici (serve all'annulla)."""
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)


def save(project: Project, path) -> None:
    profiles = {}
    fixtures = []
    for f in project.patch.fixtures:
        pid = _profile_id(f.profile)
        profiles[pid] = f.profile
        fixtures.append({"name": f.name, "profile": pid, "universe": f.universe,
                         "address": f.address, "x": f.x, "y": f.y, "rotation": f.rotation,
                         "beam_angle": f.beam_angle, "hide_beam": f.hide_beam,
                         "dimmer_min": f.dimmer_min, "dimmer_max": f.dimmer_max, "ignore_master": f.ignore_master,
                         "pan_range": f.pan_range, "tilt_range": f.tilt_range, "pan_offset": f.pan_offset,
                         "tilt_offset": f.tilt_offset, "disabled": f.disabled,
                         "beam_color": f.beam_color, "name_pos": f.name_pos, "icon_size": f.icon_size})
    doc = {"schema_version": SCHEMA_VERSION, "name": project.name, "fixtures": fixtures,
           "outputs": [{"type": o.type, "universe": o.universe, "params": o.params}
                       for o in project.outputs],
           "palettes": [{"name": p.name, "group": p.group, "presets": [{"name": x.name, "values": x.values}
                                                     for x in p.presets]} for p in project.palettes],
           "cues": [_cue_to_dict(c) for c in project.cues],
           "pages": [{"name": p.name, "priority": p.priority, "fade_time": p.fade_time,
                      "columns": p.columns, "frames": p.frames, "buttons": [vars(b) for b in p.buttons],
                      "cuelist": ({"name": p.cuelist.name, "loop": p.cuelist.loop, "priority": p.cuelist.priority,
                                   "steps": [vars(x) for x in p.cuelist.steps]} if p.cuelist else None)}
                     for p in project.pages],
           "midi_mappings": [vars(m) for m in project.midi_mappings], "osc_port": project.osc_port,
           "dmx_mappings": [vars(m) for m in project.dmx_mappings],
           "shapes": [vars(sh) for sh in project.shapes], "groups": [vars(g) for g in project.groups], "has_background": project.background is not None}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        _w(z, "project.json", json.dumps(doc, indent=2, ensure_ascii=False))
        if project.background is not None:
            _w(z, "assets/background", project.background)
        for pid, prof in profiles.items():
            _w(z, f"profiles/{pid}.json", json.dumps(_profile_to_dict(prof), indent=2))


def dumps(project: Project) -> bytes:
    import io
    buf = io.BytesIO(); save(project, buf); return buf.getvalue()


def loads(data: bytes) -> Project:
    import io
    return load(io.BytesIO(data))


def load(path) -> Project:
    with zipfile.ZipFile(path) as z:
        doc = json.loads(z.read("project.json"))
        ver = doc.get("schema_version")
        if ver not in SUPPORTED_VERSIONS:
            raise ValueError(f"versione progetto non supportata: {ver}")
        profiles = {n.split("/")[-1][:-5]: _profile_from_dict(json.loads(z.read(n)))
                    for n in z.namelist() if n.startswith("profiles/") and n.endswith(".json")}
        background = z.read("assets/background") if "assets/background" in z.namelist() else None
    proj = Project(name=doc["name"])
    proj.background = background
    proj.shapes = [StageShape(**sh) for sh in doc.get("shapes", [])]
    proj.groups = [FixtureGroup(**g) for g in doc.get("groups", [])]
    for f in doc["fixtures"]:
        proj.patch.add(FixtureInstance(f["name"], profiles[f["profile"]], f["universe"],
                                       f["address"], f.get("x", 0.5), f.get("y", 0.5),
                                       f.get("rotation", 0.0), f.get("beam_angle", 30.0),
                                       f.get("hide_beam", False), f.get("dimmer_min", 0), f.get("dimmer_max", 255),
                                       f.get("ignore_master", False), f.get("pan_range", 540.0), f.get("tilt_range", 270.0),
                                       f.get("pan_offset", 0.0), f.get("tilt_offset", 0.0), f.get("disabled", False),
                                       f.get("beam_color", ""), f.get("name_pos", "below"), f.get("icon_size", 1.0)))
    proj.outputs = [OutputConfig(o["type"], o["universe"], o.get("params", {}))
                    for o in doc["outputs"]]
    proj.palettes = [Palette(p["name"], [Preset(x["name"], x["values"]) for x in p["presets"]], p.get("group", ""))
                     for p in doc.get("palettes", [])]
    proj.cues = [_cue_from_dict(c) for c in doc.get("cues", [])]
    proj.pages = [LivePage(p["name"], [LiveButton(**b) for b in p.get("buttons", [])], p.get("priority", 0),
                           p.get("fade_time", 0.0), p.get("columns", 6),
                           (CueList(p["cuelist"]["name"], [CueListStep(**x) for x in p["cuelist"]["steps"]],
                                    p["cuelist"].get("loop", False), p["cuelist"].get("priority", 10))
                            if p.get("cuelist") else None),
                           list(p.get("frames", [""]))) for p in doc.get("pages", [])]
    if not proj.pages and proj.cues:   # progetti senza pagine: tutti i cue su una pagina
        proj.pages = [LivePage("Pagina 1", [LiveButton(c.name) for c in proj.cues])]
    proj.midi_mappings = [MidiMapping(**m) for m in doc.get("midi_mappings", [])]
    proj.osc_port = doc.get("osc_port", 21600)
    proj.dmx_mappings = [DmxMapping(**m) for m in doc.get("dmx_mappings", [])]
    return proj
