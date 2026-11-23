"""Cerca nel progetto (fixture, gruppi, palette, cue, pagine live)."""
from __future__ import annotations

SCOPES = ("fixture", "gruppo", "palette", "cue", "pagina")


def search(project, query: str, scopes=SCOPES) -> list[tuple[str, str, str]]:
    """Ritorna [(scope, nome, dettaglio)]; ricerca case-insensitive per sottostringa."""
    q = query.strip().lower()
    if not q:
        return []
    out = []
    def hit(*texts):
        return any(q in (t or "").lower() for t in texts)
    if "fixture" in scopes:
        out += [("fixture", f.name, f"{f.profile.manufacturer} {f.profile.model} U{f.universe}.{f.address}")
                for f in project.patch.fixtures if hit(f.name, f.profile.manufacturer, f.profile.model, f.profile.mode)]
    if "gruppo" in scopes:
        out += [("gruppo", g.name, f"{len(g.fixtures)} fixture") for g in project.groups if hit(g.name)]
    if "palette" in scopes:
        for pal in project.palettes:
            out += [("palette", x.name, pal.name) for x in pal.presets if hit(x.name, pal.name, pal.group)]
    if "cue" in scopes:
        out += [("cue", c.name, "") for c in project.cues if hit(c.name)]
    if "pagina" in scopes:
        for pg in project.pages:
            if hit(pg.name):
                out.append(("pagina", pg.name, ""))
            out += [("pagina", b.label or b.cue, pg.name) for b in pg.buttons if hit(b.label, b.cue)]
    return out
