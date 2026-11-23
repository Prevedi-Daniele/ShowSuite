"""Strumenti di patch: duplica, riassegna profilo/indirizzo, stampa (HTML), export/import fixture."""
from __future__ import annotations

import dataclasses
import html
import json

from .fixtures import FixtureInstance, PatchError
from .project import _profile_from_dict, _profile_to_dict


def _unique(patch, base: str) -> str:
    names = {f.name for f in patch.fixtures}
    n = 2; name = f"{base} {n}"
    while name in names:
        n += 1; name = f"{base} {n}"
    return name


def duplicate_fixtures(patch, names: list[str]) -> list[FixtureInstance]:
    """Duplica i fixture nel primo spazio libero dello stesso universo (stessa posizione spostata un po')."""
    out = []
    for n in names:
        o = patch.find(n)
        a = patch.next_free(o.universe, o.profile.footprint)
        if a is None:
            raise PatchError(f"nessuno spazio libero per {o.name} nell'universo {o.universe}")
        out.append(patch.add(dataclasses.replace(o, name=_unique(patch, o.name), address=a,
                                                 x=min(1.0, o.x + 0.03), y=min(1.0, o.y + 0.03))))
    return out


def change_address(patch, name: str, universe: int, address: int) -> FixtureInstance:
    old = patch.find(name); new = dataclasses.replace(old, universe=universe, address=address)
    patch.fixtures.remove(old)
    try:
        patch.add(new)
    except PatchError:
        patch.fixtures.append(old); raise
    patch.fixtures.sort(key=lambda f: 0)      # ordine stabile
    return new


def reassign_profile(engine, name: str, profile) -> FixtureInstance:
    """Cambia profilo mantenendo nome e indirizzo; azzera i valori del programmer del fixture."""
    patch = engine.project.patch
    old = patch.find(name); new = dataclasses.replace(old, profile=profile)
    i = patch.fixtures.index(old); patch.fixtures.remove(old)
    try:
        patch.add(new)
    except PatchError:
        patch.fixtures.insert(i, old); raise
    patch.fixtures.insert(i, patch.fixtures.pop())     # mantiene la posizione nell'elenco
    engine.values.pop(name, None)
    return new


def patch_rows(patch) -> list[tuple]:
    return [(f.universe, f.address, f.end_address, f.name, f"{f.profile.manufacturer} {f.profile.model}".strip(),
             f.profile.mode, f.profile.footprint) for f in sorted(patch.fixtures, key=lambda f: (f.universe, f.address))]


def patch_html(project) -> str:
    head = ("Universo", "Da", "A", "Nome", "Fixture", "Modalità", "Canali")
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in patch_rows(project.patch))
    return (f"<h2>{html.escape(project.name)} — Patch</h2><table border='1' cellspacing='0' cellpadding='4'>"
            "<tr>" + "".join(f"<th>{h}</th>" for h in head) + f"</tr>{rows}</table>")


def export_fixtures(patch, names: list[str], path: str) -> None:
    fx = [patch.find(n) for n in names]
    doc = {"fixtures": [{**{k: v for k, v in dataclasses.asdict(f).items() if k != "profile"},
                         "profile": _profile_to_dict(f.profile)} for f in fx]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)


def import_fixtures(patch, path: str) -> list[FixtureInstance]:
    """Importa i fixture: se l'indirizzo è occupato usa il primo spazio libero; nomi duplicati rinominati."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = []
    for d in doc["fixtures"]:
        d = dict(d); prof = _profile_from_dict(d.pop("profile"))
        fx = FixtureInstance(profile=prof, **d)
        if any(f.name == fx.name for f in patch.fixtures):
            fx = dataclasses.replace(fx, name=_unique(patch, fx.name))
        try:
            out.append(patch.add(fx))
        except PatchError:
            a = patch.next_free(fx.universe, prof.footprint)
            if a is None:
                raise
            out.append(patch.add(dataclasses.replace(fx, address=a)))
    return out
