"""Copia e incolla delle proprietà dei cue (manuale QLab 5: Paste Cue Properties).

Le proprietà sono raggruppate; si incollano solo i gruppi scelti. I gruppi che dipendono dal tipo (parametri,
effetti) si applicano solo ai cue dello stesso tipo del cue copiato. Numero, nome, target e figli non si incollano mai."""
from __future__ import annotations

import copy

from .model import Cue

GROUPS = {
    "timing": ("Tempi (pre-wait, durata, post-wait, continue)", ("pre_wait", "duration", "post_wait", "continue_mode")),
    "appearance": ("Aspetto (colore, condizione colore, note, flag)", ("color", "color_condition", "notes", "flagged")),
    "state": ("Stato (armed, auto load)", ("armed", "auto_load")),
    "triggers": ("Trigger", ("triggers", "second_trigger_action", "second_trigger_on_release")),
    "others": ("Fade/duck altri cue", ("fade_and_stop_others", "duck_others")),
    "params": ("Parametri specifici del tipo", ()),
}


def copy_properties(cue: Cue) -> dict:
    snapshot = {"cue_type": cue.cue_type, "params": copy.deepcopy(cue.params)}
    for _title, attributes in GROUPS.values():
        for attribute in attributes:
            snapshot[attribute] = copy.deepcopy(getattr(cue, attribute))
    return snapshot


def paste_properties(snapshot: dict, targets: list, groups: list) -> int:
    """Incolla i gruppi indicati sui cue di `targets`; ritorna quanti cue sono stati modificati."""
    changed = 0
    for cue in targets:
        touched = False
        for group in groups:
            if group not in GROUPS:
                raise ValueError("gruppo sconosciuto: " + group)
            if group == "params":
                if cue.cue_type == snapshot["cue_type"]:
                    cue.params = copy.deepcopy(snapshot["params"])
                    touched = True
                continue
            for attribute in GROUPS[group][1]:
                setattr(cue, attribute, copy.deepcopy(snapshot[attribute]))
                touched = True
        if touched == True:
            changed = changed + 1
    return changed
