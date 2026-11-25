"""Motore di esecuzione della sezione Cue (headless, senza PySide6).

Il tempo è guidato da un `Clock`: `ManualClock` nei test (deterministico), `SystemClock` in produzione. Chi usa il
motore chiama `update()` a intervalli regolari (UI o thread); `advance(delta)` fa avanzare esplicitamente il tempo
processando gli eventi nell'ordine in cui scadono.

Le uscite reali (audio, video, MIDI, rete, luci) sono `ActionHandler` registrati per tipo di cue: il motore si
occupa di tempi, sequenze, gruppi, trigger secondari, cue di controllo e fade dei parametri."""
from __future__ import annotations

import math
import os
import random
import threading
import time

from . import curves
from .model import (CONTINUE_AUTO_CONTINUE, CONTINUE_AUTO_FOLLOW, CONTINUE_NONE, GROUP_CART, GROUP_LIST,
                    GROUP_PLAYLIST, GROUP_START_FIRST, GROUP_START_FIRST_AND_ENTER, GROUP_START_RANDOM,
                    GROUP_TIMELINE, INSTANT_TYPES, TYPE_ARM, TYPE_AUDIO, TYPE_CAMERA, TYPE_CART, TYPE_DEVAMP,
                    TYPE_DISARM, TYPE_FADE, TYPE_GOTO, TYPE_GROUP, TYPE_LIGHT, TYPE_LIST, TYPE_LOAD, TYPE_MEMO,
                    TYPE_MIC, TYPE_MIDI, TYPE_MIDI_FILE, TYPE_NETWORK, TYPE_PAUSE, TYPE_RESET, TYPE_SCRIPT,
                    TYPE_START, TYPE_STOP, TYPE_TARGET, TYPE_TEXT, TYPE_TIMECODE, TYPE_VIDEO, TYPE_WAIT, Cue,
                    Workspace)
from .playback import INFINITE, PlaybackPlan
from .timeutil import MINUS_INFINITY, db_to_linear, linear_to_db

EPSILON = 1e-9

SECOND_TRIGGER_NONE = 0
SECOND_TRIGGER_PANIC = 1
SECOND_TRIGGER_STOP = 2
SECOND_TRIGGER_HARD_STOP = 3
SECOND_TRIGGER_HARD_STOP_RESTART = 4
SECOND_TRIGGER_DEVAMP = 5
SECOND_TRIGGER_PLAYLIST_NEXT = 6
SECOND_TRIGGER_PLAYLIST_PREVIOUS = 7

ORIGIN_GO = "go"
ORIGIN_TRIGGER = "trigger"
ORIGIN_CONTINUE = "continue"
ORIGIN_START_CUE = "start_cue"
ORIGIN_GROUP = "group"
ORIGIN_OSC = "osc"
ORIGIN_SCRIPT = "script"


class ManualClock:
    def __init__(self, start: float = 0.0):
        self.value = start

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value = self.value + seconds


class SystemClock:
    def now(self) -> float:
        return time.monotonic()


class ActionHandler:
    """Interfaccia delle uscite. Tutti i metodi sono opzionali (no-op)."""

    def start(self, runtime: "Runtime", state: "CueState") -> None:
        pass

    def stop(self, runtime: "Runtime", state: "CueState", hard: bool) -> None:
        pass

    def panic(self, runtime: "Runtime", state: "CueState", duration: float) -> None:
        pass

    def pause(self, runtime: "Runtime", state: "CueState") -> None:
        pass

    def resume(self, runtime: "Runtime", state: "CueState") -> None:
        pass

    def load(self, runtime: "Runtime", cue: Cue, seconds: float | None) -> None:
        pass

    def update(self, runtime: "Runtime", state: "CueState") -> None:
        pass

    def parameters_changed(self, runtime: "Runtime", cue: Cue, changes: dict) -> None:
        pass


class CueState:
    """Stato di esecuzione (runtime) di un cue avviato. Non viene mai salvato nel documento."""

    def __init__(self, cue: Cue, origin: str, preview: bool, audition: bool):
        self.cue = cue
        self.origin = origin
        self.preview = preview
        self.audition = audition
        self.pre_wait_running = False
        self.action_running = False
        self.post_wait_running = False
        self.paused = False
        self.panicking = False
        self.panic_elapsed = 0.0
        self.crossfading_out = False
        self.tailing_out = False
        self.pre_wait_elapsed = 0.0
        self.action_elapsed = 0.0
        self.post_wait_elapsed = 0.0
        self.action_duration = 0.0
        self.pre_wait_total = 0.0
        self.post_wait_total = 0.0
        self.follow_at: float | None = None
        self.followed = False
        self.plan: PlaybackPlan | None = None
        self.group_started = False
        self.children_ready = False
        self.fade_data: dict | None = None
        self.fade_out: dict | None = None
        self.devamp_watchers: list = []
        self.error = ""
        self.virtual = False

    def is_active(self) -> bool:
        return self.pre_wait_running or self.action_running or self.post_wait_running or self.fade_out is not None


class ScriptApi:
    """API esposta agli Script cue Python: `workspace`, `cue(numero)`, `go()`, `log(...)`."""

    def __init__(self, runtime: "Runtime", messages: list):
        self._runtime = runtime
        self._messages = messages
        self.workspace = runtime.workspace

    def cue(self, number_or_id: str):
        found = self._runtime.workspace.find_by_number(str(number_or_id))
        if found is None:
            found = self._runtime.workspace.find_by_id(str(number_or_id))
        if found is None:
            raise KeyError("cue non trovato: " + str(number_or_id))
        return ScriptCue(self._runtime, found)

    def go(self) -> None:
        self._runtime.go(origin=ORIGIN_SCRIPT, ignore_min_go_time=True)

    def log(self, *values) -> None:
        self._messages.append(" ".join(str(value) for value in values))

    def send_osc(self, address: str, *arguments) -> None:
        self._runtime.emit("script_osc", None, {"address": address, "arguments": list(arguments)})


class ScriptCue:
    def __init__(self, runtime: "Runtime", cue: Cue):
        self._runtime = runtime
        self._cue = cue

    @property
    def name(self) -> str:
        return self._cue.display_name(self._runtime.workspace)

    @property
    def number(self) -> str:
        return self._cue.number

    @property
    def running(self) -> bool:
        return self._runtime.is_running(self._cue)

    def start(self) -> None:
        self._runtime.start_cue(self._cue, origin=ORIGIN_SCRIPT)

    def stop(self) -> None:
        self._runtime.stop_cue(self._cue)

    def pause(self) -> None:
        self._runtime.pause_cue(self._cue)

    def resume(self) -> None:
        self._runtime.resume_cue(self._cue)

    def reset(self) -> None:
        self._runtime.reset_cue(self._cue)

    def load(self) -> None:
        self._runtime.load_cue(self._cue)

    def arm(self) -> None:
        self._cue.armed = True

    def disarm(self) -> None:
        self._cue.armed = False


def _safe_builtins() -> dict:
    import builtins
    names = ["abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min", "print",
             "range", "round", "sorted", "str", "sum", "zip", "True", "False", "None", "Exception", "ValueError",
             "KeyError"]
    return {name: getattr(builtins, name) for name in names}


class Runtime:
    def __init__(self, workspace: Workspace, clock=None, check_files: bool = False, random_source=None):
        self.workspace = workspace
        self.clock = clock if clock is not None else SystemClock()
        self.check_files = check_files
        self.random = random_source if random_source is not None else random.Random()
        self.handlers: dict[str, ActionHandler] = {}
        self.states: dict[str, CueState] = {}
        self.playheads: dict[str, str] = {}
        self.fired: set[str] = set()
        self.loaded: dict[str, float | None] = {}
        self.temp_targets: dict[str, str] = {}
        self.live: dict[str, dict] = {}
        self.gains: dict[str, float] = {}
        self.duck_sources: dict[str, dict] = {}
        self.random_memory: dict[str, set] = {}
        self.playlist_order: dict[str, list] = {}
        self.selection: list[str] = []
        self.listeners: list = []
        self.log: list = []
        self.script_output: list[str] = []
        self.light_bridge = None
        self.lock = threading.RLock()
        self.panic_timer = 0.0
        self._last_time = self.clock.now()
        self._last_go_time = -math.inf
        self._fade_snapshots: dict[str, dict] = {}
        self.reset_workspace(load=False)

    # ------------------------------------------------------------------ eventi
    def emit(self, name: str, cue: Cue | None, data: dict | None = None) -> None:
        entry = (name, cue.unique_id if cue is not None else "", data if data is not None else {})
        self.log.append(entry)
        if len(self.log) > 20000:
            del self.log[:5000]
        for listener in list(self.listeners):
            listener(name, cue, entry[2])

    def events(self, name: str | None = None) -> list:
        return [entry for entry in self.log if name is None or entry[0] == name]

    def register_handler(self, cue_type: str, handler: ActionHandler) -> None:
        self.handlers[cue_type] = handler

    def _handler(self, cue: Cue) -> ActionHandler | None:
        return self.handlers.get(cue.cue_type)

    # ------------------------------------------------------------------ target e parametri live
    def resolve_target(self, cue: Cue) -> Cue | None:
        temporary = self.temp_targets.get(cue.unique_id, "")
        if temporary != "":
            found = self.workspace.find_by_id(temporary)
            if found is not None:
                return found
        return self.workspace.find_target(cue)

    def get_param(self, cue: Cue, name: str, default=None):
        overrides = self.live.get(cue.unique_id, {})
        if name in overrides:
            return overrides[name]
        return cue.params.get(name, default)

    def set_live_param(self, cue: Cue, name: str, value) -> None:
        self.live.setdefault(cue.unique_id, {})[name] = value
        handler = self._handler(cue)
        if handler is not None:
            handler.parameters_changed(self, cue, {name: value})

    def gain_for(self, cue: Cue) -> float:
        return self.gains.get(cue.unique_id, 1.0)

    # ------------------------------------------------------------------ durate e controlli di validità
    def media_duration(self, cue: Cue) -> float | None:
        return cue.params.get("media_duration", None)

    def make_plan(self, cue: Cue) -> PlaybackPlan:
        return PlaybackPlan(cue.params, self.media_duration(cue))

    def action_duration(self, cue: Cue, plan: PlaybackPlan | None = None) -> float:
        cue_type = cue.cue_type
        if cue_type in (TYPE_AUDIO, TYPE_VIDEO):
            media = self.media_duration(cue)
            if media is None and cue_type == TYPE_VIDEO:
                return INFINITE
            if plan is None:
                plan = self.make_plan(cue)
            return plan.total_duration()
        if cue_type in (TYPE_MIC, TYPE_CAMERA):
            return INFINITE
        if cue_type == TYPE_MIDI_FILE:
            media = self.media_duration(cue)
            if media is None:
                return 0.0
            return float(media) / max(0.01, float(cue.params.get("playback_rate", 1.0)))
        if cue_type == TYPE_TIMECODE:
            stop_after = cue.params.get("stop_after", None)
            return INFINITE if stop_after is None else float(stop_after)
        if cue_type == TYPE_TEXT:
            return cue.duration if cue.duration > 0 else INFINITE
        if cue_type in INSTANT_TYPES:
            return 0.0
        if cue_type in (TYPE_GROUP, TYPE_LIST, TYPE_CART):
            return INFINITE
        return max(0.0, float(cue.duration))

    def broken_reason(self, cue: Cue) -> str:
        cue_type = cue.cue_type
        if cue_type in (TYPE_AUDIO, TYPE_VIDEO, TYPE_MIDI_FILE):
            path = cue.params.get("file_target", "")
            if path == "":
                return "nessun file"
            if self.check_files == True and os.path.exists(path) == False:
                return "file mancante"
            if cue_type in (TYPE_AUDIO, TYPE_VIDEO) and self.media_duration(cue) is not None:
                if self.make_plan(cue).is_playable() == False:
                    return "tutte le slice hanno play count 0"
        if cue.has_cue_target() == True and cue_type != TYPE_TARGET:
            if self.resolve_target(cue) is None:
                return "nessun target"
        if cue_type == TYPE_TARGET:
            if self.workspace.find_target(cue) is None:
                return "nessun target"
            if cue.params.get("new_target_number", "") == "":
                return "manca il nuovo numero di target"
            new_target = self.workspace.find_by_number(str(cue.params["new_target_number"]))
            if new_target is None:
                return "il nuovo target non esiste"
            if self.workspace.find_target(cue).cue_type == TYPE_FADE:
                return "un Target cue non può agire su un Fade"
        if cue_type == TYPE_FADE:
            target = self.resolve_target(cue)
            if target is not None and self.fade_parameters(cue) == []:
                return "nessun parametro attivo"
        if cue_type == TYPE_SCRIPT and cue.params.get("compile_error", "") != "":
            return "errore di script"
        if cue_type == TYPE_NETWORK and str(cue.params.get("message", "")).strip() == "":
            return "messaggio mancante"
        parent = cue.parent
        if parent is not None and parent.cue_type == TYPE_GROUP:
            mode = parent.group_mode()
            if mode == GROUP_TIMELINE and cue.continue_mode != CONTINUE_NONE:
                return "un figlio di una Timeline non può avere continue"
            if mode == GROUP_PLAYLIST and parent.params.get("playlist_crossfade", False) == True:
                crossfade = float(parent.params.get("playlist_crossfade_duration", 0.05))
                duration = self.action_duration(cue)
                if duration != INFINITE and duration <= crossfade and cue.cue_type not in INSTANT_TYPES:
                    return "figlio più corto del crossfade"
        if cue_type == TYPE_GROUP and cue.group_mode() == GROUP_PLAYLIST:
            if cue.params.get("playlist_loop", False) == True:
                has_duration = False
                for child in cue.children:
                    child_duration = self.action_duration(child)
                    if child_duration > 0:
                        has_duration = True
                if has_duration == False:
                    return "loop senza figli con durata"
        return ""

    def is_broken(self, cue: Cue) -> bool:
        return self.broken_reason(cue) != ""

    # ------------------------------------------------------------------ sequenze e playhead
    def sequence_cues(self, cue: Cue) -> list[Cue]:
        """Il cue e i successivi collegati da auto-continue/auto-follow (stesso genitore)."""
        result = [cue]
        current = cue
        guard = 0
        while self.effective_continue(current) != CONTINUE_NONE and guard < 100000:
            following = self.next_sibling(current)
            if following is None or following in result:
                break
            result.append(following)
            current = following
            guard = guard + 1
        return result

    def effective_continue(self, cue: Cue) -> int:
        parent = cue.parent
        if parent is not None and parent.cue_type == TYPE_GROUP and parent.group_mode() == GROUP_PLAYLIST:
            return CONTINUE_AUTO_FOLLOW
        if parent is not None and parent.cue_type == TYPE_CART:
            return CONTINUE_NONE
        return cue.continue_mode

    def next_sibling(self, cue: Cue) -> Cue | None:
        parent = cue.parent
        if parent is None:
            return None
        siblings = self._ordered_children(parent)
        position = siblings.index(cue)
        if position + 1 < len(siblings):
            return siblings[position + 1]
        if parent.cue_type == TYPE_GROUP and parent.group_mode() == GROUP_PLAYLIST:
            if parent.params.get("playlist_loop", False) == True and self.is_broken(parent) == False:
                return siblings[0]
        return None

    def previous_sibling(self, cue: Cue) -> Cue | None:
        parent = cue.parent
        if parent is None:
            return None
        siblings = self._ordered_children(parent)
        position = siblings.index(cue)
        if position > 0:
            return siblings[position - 1]
        if parent.cue_type == TYPE_GROUP and parent.group_mode() == GROUP_PLAYLIST:
            if parent.params.get("playlist_loop", False) == True:
                return siblings[-1]
        return None

    def _ordered_children(self, parent: Cue) -> list[Cue]:
        order = self.playlist_order.get(parent.unique_id)
        if order is None:
            return list(parent.children)
        by_id = {child.unique_id: child for child in parent.children}
        result = [by_id[identifier] for identifier in order if identifier in by_id]
        for child in parent.children:
            if child not in result:
                result.append(child)
        return result

    def next_after(self, cue: Cue) -> Cue | None:
        """Il cue che segue (anche uscendo dai Group) per il playhead."""
        node = cue
        while node is not None and node.parent is not None:
            parent = node.parent
            siblings = parent.children
            position = siblings.index(node)
            if position + 1 < len(siblings):
                return siblings[position + 1]
            if parent.cue_type != TYPE_GROUP:
                return None
            node = parent
        return None

    def playhead(self, container: Cue | None = None) -> Cue | None:
        if container is None:
            container = self.workspace.active_list()
        identifier = self.playheads.get(container.unique_id, "")
        if identifier == "":
            return None
        return self.workspace.find_by_id(identifier)

    def set_playhead(self, cue: Cue | None, container: Cue | None = None) -> None:
        if cue is not None:
            container = cue.root_list()
        if container is None:
            container = self.workspace.active_list()
        self.playheads[container.unique_id] = cue.unique_id if cue is not None else ""
        self.emit("playhead", cue, {"list": container.unique_id})

    def _first_cue_of(self, container: Cue) -> Cue | None:
        if len(container.children) == 0:
            return None
        return container.children[0]

    def move_playhead_next(self, container: Cue | None = None) -> None:
        container = container if container is not None else self.workspace.active_list()
        current = self.playhead(container)
        if current is None:
            return
        following = self.next_after(current)
        if following is not None:
            self.set_playhead(following, container)

    def move_playhead_previous(self, container: Cue | None = None) -> None:
        container = container if container is not None else self.workspace.active_list()
        current = self.playhead(container)
        if current is None:
            self.set_playhead(self._last_cue_of(container), container)
            return
        node = current
        siblings = node.parent.children
        position = siblings.index(node)
        if position > 0:
            self.set_playhead(siblings[position - 1], container)
        elif node.parent.cue_type == TYPE_GROUP:
            self.set_playhead(node.parent, container)

    def _last_cue_of(self, container: Cue) -> Cue | None:
        if len(container.children) == 0:
            return None
        return container.children[-1]

    def sequence_starts(self, container: Cue) -> list[Cue]:
        """Primo cue di ogni sequenza della lista (per next/previous sequence)."""
        starts: list[Cue] = []
        inside_sequence = False
        for cue in container.children:
            if inside_sequence == False:
                starts.append(cue)
            inside_sequence = self.effective_continue(cue) != CONTINUE_NONE
        return starts

    def move_playhead_next_sequence(self, container: Cue | None = None) -> None:
        container = container if container is not None else self.workspace.active_list()
        current = self.playhead(container)
        starts = self.sequence_starts(container)
        for start in starts:
            if current is None or container.children.index(start) > container.children.index(current):
                self.set_playhead(start, container)
                return

    def move_playhead_previous_sequence(self, container: Cue | None = None) -> None:
        container = container if container is not None else self.workspace.active_list()
        current = self.playhead(container)
        starts = self.sequence_starts(container)
        previous = None
        for start in starts:
            if current is not None and container.children.index(start) < container.children.index(current):
                previous = start
        if previous is not None:
            self.set_playhead(previous, container)

    def set_selection(self, cues: list[Cue]) -> None:
        self.selection = [cue.unique_id for cue in cues]
        if self.workspace.settings.get("lock_playhead_to_selection", False) == True and len(cues) > 0:
            self.set_playhead(cues[0])

    # ------------------------------------------------------------------ GO e avvio
    def go(self, container: Cue | None = None, origin: str = ORIGIN_GO, ignore_min_go_time: bool = False,
           audition: bool = False) -> bool:
        container = container if container is not None else self.workspace.active_list()
        now = self.clock.now()
        minimum = float(self.workspace.settings.get("min_go_time", 0.0))
        if ignore_min_go_time == False and minimum > 0 and now - self._last_go_time < minimum - EPSILON:
            self.emit("go_ignored", None, {"reason": "double_go"})
            return False
        if container.cue_type == TYPE_CART:
            return False
        cue = self.playhead(container)
        if cue is None:
            return False
        self._last_go_time = now
        sequence = self.sequence_cues(cue)
        self.start_cue(cue, origin=origin, audition=audition)
        last_cue = sequence[-1]
        if cue.cue_type == TYPE_GROUP and cue.group_mode() == GROUP_START_FIRST_AND_ENTER and len(cue.children) > 1:
            self.set_playhead(cue.children[1], container)
        else:
            self.set_playhead(self.next_after(last_cue), container)
            if self.playhead(container) is None:
                self.playheads[container.unique_id] = ""
        return True

    def preview(self, cue: Cue | None = None, audition: bool = False) -> bool:
        if cue is None:
            cue = self.playhead()
        if cue is None:
            return False
        return self.start_cue(cue, origin=ORIGIN_GO, preview=True, audition=audition)

    def start_cue(self, cue: Cue, origin: str = ORIGIN_START_CUE, preview: bool = False,
                  audition: bool = False) -> bool:
        if cue.cue_type == TYPE_LIST:
            return self.go(cue, origin=origin, ignore_min_go_time=True)
        if cue.cue_type == TYPE_CART:
            return False
        existing = self.states.get(cue.unique_id)
        if existing is not None and existing.is_active() == True:
            if origin == ORIGIN_TRIGGER:
                return self._second_trigger(cue, existing)
            if existing.paused == True:
                self.resume_cue(cue)
                return True
            return False
        state = CueState(cue, origin, preview, audition)
        self.states[cue.unique_id] = state
        state.pre_wait_total = 0.0 if preview == True else max(0.0, float(cue.pre_wait))
        state.post_wait_total = self._effective_post_wait(cue)
        self.emit("start", cue, {"origin": origin, "preview": preview})
        if state.pre_wait_total > EPSILON:
            state.pre_wait_running = True
            self.emit("pre_wait_start", cue, {})
        else:
            self._begin_action(state)
        self._process_due()
        return True

    def _effective_post_wait(self, cue: Cue) -> float:
        if cue.cue_type == TYPE_WAIT:
            return max(0.0, float(cue.duration))
        parent = cue.parent
        if parent is not None and parent.cue_type == TYPE_GROUP and parent.group_mode() == GROUP_PLAYLIST:
            duration = self.action_duration(cue)
            return 0.0 if duration == INFINITE else duration
        if cue.continue_mode == CONTINUE_AUTO_FOLLOW:
            duration = self.action_duration(cue)
            return 0.0 if duration == INFINITE else duration
        return max(0.0, float(cue.post_wait))

    def _begin_action(self, state: CueState) -> None:
        cue = state.cue
        state.pre_wait_running = False
        state.action_running = True
        state.action_elapsed = 0.0
        if state.preview == False and self.effective_continue(cue) == CONTINUE_AUTO_CONTINUE:
            state.post_wait_running = True
            state.post_wait_elapsed = 0.0
        broken = self.broken_reason(cue)
        state.virtual = broken != "" or cue.armed == False
        if cue.cue_type in (TYPE_AUDIO, TYPE_VIDEO) and broken == "":
            state.plan = self.make_plan(cue)
            state.action_duration = self.action_duration(cue, state.plan)
        else:
            state.action_duration = self.action_duration(cue)
        self._schedule_playlist_crossfade(state)
        self.fired.add(cue.unique_id)
        self.emit("action_start", cue, {"virtual": state.virtual, "broken": broken})
        if state.virtual == True:
            if cue.is_group_like() == True:
                state.group_started = True
            return
        self._apply_start_side_effects(state)
        self._run_action(state)

    def _schedule_playlist_crossfade(self, state: CueState) -> None:
        cue = state.cue
        parent = cue.parent
        if parent is None or parent.cue_type != TYPE_GROUP or parent.group_mode() != GROUP_PLAYLIST:
            return
        if parent.params.get("playlist_crossfade", False) == False:
            return
        crossfade = float(parent.params.get("playlist_crossfade_duration", 0.05))
        if state.action_duration != INFINITE and state.action_duration > crossfade:
            state.follow_at = state.action_duration - crossfade

    def _apply_start_side_effects(self, state: CueState) -> None:
        cue = state.cue
        mode = int(cue.fade_and_stop_others.get("mode", 0))
        if mode != 0:
            self._fade_and_stop_others(state, mode, float(cue.fade_and_stop_others.get("time", 0.0)))
        if cue.duck_others.get("enabled", False) == True:
            self._duck_others(state)
        # un cue in una playlist con crossfade: il precedente sfuma in uscita
        self.loaded.pop(cue.unique_id, None)

    def _fade_and_stop_others(self, state: CueState, mode: int, seconds: float) -> None:
        source = state.cue
        for other in list(self.states.values()):
            if other is state or other.is_active() == False:
                continue
            candidate = other.cue
            if candidate in list(source.ancestors()) or source in list(candidate.ancestors()):
                continue
            if mode == 1 and candidate.parent is not source.parent:
                continue
            if mode == 2 and candidate.root_list() is not source.root_list():
                continue
            if candidate.cue_type in (TYPE_GROUP,):
                continue
            if seconds <= EPSILON:
                self.stop_cue(candidate, hard=True)
            else:
                other.fade_out = {"time": seconds, "elapsed": 0.0}
                self.emit("fade_out_others", candidate, {"time": seconds})

    def _duck_others(self, state: CueState) -> None:
        source = state.cue
        level = float(source.duck_others.get("level", -12.0))
        seconds = float(source.duck_others.get("time", 1.0))
        affected = []
        for other in self.states.values():
            if other is state or other.is_active() == False:
                continue
            if other.cue.cue_type not in (TYPE_AUDIO, TYPE_VIDEO, TYPE_MIC, TYPE_CAMERA):
                continue
            if other.cue.root_list() is not source.root_list():
                continue
            affected.append(other.cue.unique_id)
            self.gains[other.cue.unique_id] = db_to_linear(level)
        self.duck_sources[source.unique_id] = {"cues": affected, "level": level, "time": seconds}
        self.emit("duck", source, {"level": level, "time": seconds, "cues": list(affected)})

    def _release_duck(self, source: Cue) -> None:
        info = self.duck_sources.pop(source.unique_id, None)
        if info is None:
            return
        for identifier in info["cues"]:
            self.gains.pop(identifier, None)
        self.emit("unduck", source, {})

    def _run_action(self, state: CueState) -> None:
        cue = state.cue
        cue_type = cue.cue_type
        if cue_type == TYPE_GROUP:
            self._start_group(state)
        elif cue_type == TYPE_START:
            target = self.resolve_target(cue)
            self.start_cue(target, origin=ORIGIN_START_CUE)
        elif cue_type == TYPE_STOP:
            self.stop_cue(self.resolve_target(cue))
        elif cue_type == TYPE_PAUSE:
            self.pause_cue(self.resolve_target(cue))
        elif cue_type == TYPE_LOAD:
            self.load_cue(self.resolve_target(cue), float(cue.params.get("load_time", 0.0)) or None)
        elif cue_type == TYPE_RESET:
            self.reset_cue(self.resolve_target(cue))
        elif cue_type == TYPE_ARM:
            self.arm_cue(self.resolve_target(cue), True)
        elif cue_type == TYPE_DISARM:
            self.arm_cue(self.resolve_target(cue), False)
        elif cue_type == TYPE_GOTO:
            self.goto_cue(self.resolve_target(cue))
        elif cue_type == TYPE_TARGET:
            self._run_target_cue(cue)
        elif cue_type == TYPE_DEVAMP:
            self._run_devamp(state)
        elif cue_type == TYPE_FADE:
            self._start_fade(state)
        elif cue_type == TYPE_SCRIPT:
            self._run_script(state)
        handler = self._handler(cue)
        if handler is not None:
            handler.start(self, state)

    # ------------------------------------------------------------------ gruppi
    def _start_group(self, state: CueState) -> None:
        group = state.cue
        mode = group.group_mode()
        children = list(group.children)
        state.group_started = True
        if len(children) == 0:
            return
        if mode == GROUP_TIMELINE:
            for child in children:
                self.start_cue(child, origin=ORIGIN_GROUP)
        elif mode == GROUP_PLAYLIST:
            order = [child.unique_id for child in children]
            if group.params.get("playlist_shuffle", False) == True:
                self.random.shuffle(order)
            self.playlist_order[group.unique_id] = order
            first = self._ordered_children(group)[0]
            self.start_cue(first, origin=ORIGIN_GROUP)
        elif mode == GROUP_START_RANDOM:
            chosen = self._choose_random_child(group)
            if chosen is not None:
                self.start_cue(chosen, origin=ORIGIN_GROUP)
        else:
            self.start_cue(children[0], origin=ORIGIN_GROUP)

    def _choose_random_child(self, group: Cue) -> Cue | None:
        memory = self.random_memory.setdefault(group.unique_id, set())
        for attempt in range(2):
            candidates = []
            for child in group.children:
                if child.armed == False:
                    continue
                running = self.states.get(child.unique_id)
                if running is not None and running.is_active() == True:
                    continue
                if child.unique_id in memory:
                    continue
                candidates.append(child)
            if len(candidates) > 0:
                chosen = self.random.choice(candidates)
                memory.add(chosen.unique_id)
                return chosen
            memory.clear()
        return None

    def _group_has_active_descendants(self, group: Cue) -> bool:
        for node in group.walk():
            if node is group:
                continue
            found = self.states.get(node.unique_id)
            if found is not None and found.is_active() == True:
                return True
        return False

    def playlist_step(self, group: Cue, direction: int) -> bool:
        """Play next / previous di una Playlist in esecuzione (rispetta loop e crossfade)."""
        if group.group_mode() != GROUP_PLAYLIST:
            return False
        current = None
        for child in self._ordered_children(group):
            found = self.states.get(child.unique_id)
            if found is not None and found.action_running == True and found.crossfading_out == False:
                current = child
        if current is None:
            return False
        target = self.next_sibling(current) if direction > 0 else self.previous_sibling(current)
        if target is None:
            return False
        self.stop_cue(current)
        self.start_cue(target, origin=ORIGIN_GROUP)
        return True

    # ------------------------------------------------------------------ second trigger
    def _second_trigger(self, cue: Cue, state: CueState) -> bool:
        action = int(cue.second_trigger_action)
        if action == SECOND_TRIGGER_NONE:
            return False
        self.apply_second_trigger(cue, action)
        return True

    def apply_second_trigger(self, cue: Cue, action: int) -> None:
        if action == SECOND_TRIGGER_PANIC:
            self.panic_cue(cue)
        elif action == SECOND_TRIGGER_STOP:
            self.stop_cue(cue)
        elif action == SECOND_TRIGGER_HARD_STOP:
            self.stop_cue(cue, hard=True)
        elif action == SECOND_TRIGGER_HARD_STOP_RESTART:
            self.stop_cue(cue, hard=True)
            self.start_cue(cue, origin=ORIGIN_GROUP)
        elif action == SECOND_TRIGGER_DEVAMP:
            self.devamp_cue(cue)
        elif action == SECOND_TRIGGER_PLAYLIST_NEXT:
            self.playlist_step(cue, 1)
        elif action == SECOND_TRIGGER_PLAYLIST_PREVIOUS:
            self.playlist_step(cue, -1)
        self._process_due()

    def release_trigger(self, cue: Cue) -> None:
        """Rilascio del trigger (tasto/nota): vale come secondo trigger se abilitato."""
        if cue.second_trigger_on_release == False:
            return
        state = self.states.get(cue.unique_id)
        if state is None or state.is_active() == False:
            return
        self._second_trigger(cue, state)

    # ------------------------------------------------------------------ cue di controllo
    def is_running(self, cue: Cue) -> bool:
        state = self.states.get(cue.unique_id)
        return state is not None and state.action_running == True

    def is_active(self, cue: Cue) -> bool:
        state = self.states.get(cue.unique_id)
        return state is not None and state.is_active()

    def _terminate_state(self, state: CueState, hard: bool) -> None:
        cue = state.cue
        was_running = state.action_running
        state.pre_wait_running = False
        state.action_running = False
        state.post_wait_running = False
        state.fade_out = None
        state.paused = False
        state.panicking = False
        handler = self._handler(cue)
        if handler is not None and was_running == True and state.virtual == False:
            handler.stop(self, state, hard)
        if state.fade_data is not None:
            self._finish_fade(state, completed=False)
        self._release_duck(cue)
        self.gains.pop(cue.unique_id, None)
        self.emit("stop", cue, {"hard": hard})

    def stop_cue(self, cue: Cue | None, hard: bool = False) -> None:
        if cue is None:
            return
        for node in list(cue.walk()):
            state = self.states.get(node.unique_id)
            if state is not None and state.is_active() == True:
                self._terminate_state(state, hard)
        self._prune()

    def pause_cue(self, cue: Cue | None) -> None:
        if cue is None:
            return
        for node in list(cue.walk()):
            state = self.states.get(node.unique_id)
            if state is not None and state.is_active() == True and state.paused == False:
                state.paused = True
                handler = self._handler(node)
                if handler is not None and state.virtual == False:
                    handler.pause(self, state)
                self.emit("pause", node, {})

    def resume_cue(self, cue: Cue | None) -> None:
        if cue is None:
            return
        for node in list(cue.walk()):
            state = self.states.get(node.unique_id)
            if state is not None and state.paused == True:
                state.paused = False
                handler = self._handler(node)
                if handler is not None and state.virtual == False:
                    handler.resume(self, state)
                self.emit("resume", node, {})

    def panic_cue(self, cue: Cue | None) -> None:
        if cue is None:
            return
        duration = float(self.workspace.settings.get("panic_duration", 2.0))
        for node in list(cue.walk()):
            state = self.states.get(node.unique_id)
            if state is None or state.is_active() == False:
                continue
            if state.panicking == True:
                self._terminate_state(state, True)
                continue
            state.panicking = True
            state.panic_elapsed = 0.0
            state.pre_wait_running = False
            state.post_wait_running = False
            handler = self._handler(node)
            if handler is not None and state.virtual == False:
                handler.panic(self, state, duration)
            self.emit("panic", node, {"duration": duration})
        self._prune()

    def pause_all(self) -> None:
        for state in list(self.states.values()):
            if state.is_active() == True and state.paused == False:
                self.pause_cue_single(state)

    def pause_cue_single(self, state: CueState) -> None:
        state.paused = True
        handler = self._handler(state.cue)
        if handler is not None and state.virtual == False:
            handler.pause(self, state)
        self.emit("pause", state.cue, {})

    def resume_all(self) -> None:
        for state in list(self.states.values()):
            if state.paused == True:
                state.paused = False
                handler = self._handler(state.cue)
                if handler is not None and state.virtual == False:
                    handler.resume(self, state)
                self.emit("resume", state.cue, {})

    def panic_all(self) -> None:
        for state in list(self.states.values()):
            self.panic_cue(state.cue)

    def hard_stop_all(self) -> None:
        for state in list(self.states.values()):
            if state.is_active() == True:
                self._terminate_state(state, True)
        self._prune()

    def reset_cue(self, cue: Cue | None) -> None:
        if cue is None:
            return
        self.stop_cue(cue, hard=True)
        for node in cue.walk():
            self.live.pop(node.unique_id, None)
            self.temp_targets.pop(node.unique_id, None)
            self.fired.discard(node.unique_id)
            self.gains.pop(node.unique_id, None)
            self.random_memory.pop(node.unique_id, None)
            self.playlist_order.pop(node.unique_id, None)
            self.loaded.pop(node.unique_id, None)
            self._fade_snapshots.pop(node.unique_id, None)
        self.emit("reset", cue, {})

    def reset_workspace(self, load: bool = True) -> None:
        self.hard_stop_all()
        self.live.clear()
        self.temp_targets.clear()
        self.fired.clear()
        self.gains.clear()
        self.random_memory.clear()
        self.playlist_order.clear()
        self.loaded.clear()
        self._fade_snapshots.clear()
        self.duck_sources.clear()
        for container in self.workspace.lists:
            first = self._first_cue_of(container)
            self.playheads[container.unique_id] = first.unique_id if first is not None else ""
            if load == True and first is not None and container.cue_type == TYPE_LIST:
                self.load_cue(first)

    def ensure_playheads(self) -> None:
        """Inizializza i playhead mancanti o non più validi senza fermare nulla."""
        for container in self.workspace.lists:
            identifier = self.playheads.get(container.unique_id, None)
            valid = identifier is not None and (identifier == "" and len(container.children) == 0 or (
                identifier != "" and self.workspace.find_by_id(identifier) is not None))
            if valid == False:
                first = self._first_cue_of(container)
                self.playheads[container.unique_id] = first.unique_id if first is not None else ""

    def load_cue(self, cue: Cue | None, seconds: float | None = None, ignore_pre_wait: bool = False) -> None:
        """Prepara il cue (e la sua sequenza). seconds<0 = a |seconds| dalla fine."""
        if cue is None:
            return
        if cue.parent is not None:
            targets = self.sequence_cues(cue)
        else:
            targets = [cue]
        for item in targets:
            resolved = seconds
            if seconds is not None and seconds < 0:
                duration = self.action_duration(item)
                if duration != INFINITE:
                    resolved = max(0.0, duration + seconds)
                else:
                    resolved = 0.0
            self.loaded[item.unique_id] = resolved
            handler = self._handler(item)
            if handler is not None:
                handler.load(self, item, resolved)
            self.emit("load", item, {"time": resolved})

    def arm_cue(self, cue: Cue | None, armed: bool) -> None:
        if cue is None:
            return
        cue.armed = armed
        self.workspace.modified = True
        self.emit("arm" if armed == True else "disarm", cue, {})

    def goto_cue(self, cue: Cue | None) -> None:
        if cue is None:
            return
        if cue.is_container() == True:
            first = self._first_cue_of(cue)
            self.set_playhead(first, cue)
            return
        self.set_playhead(cue)

    def _run_target_cue(self, cue: Cue) -> None:
        target = self.workspace.find_target(cue)
        new_target = self.workspace.find_by_number(str(cue.params.get("new_target_number", "")))
        if target is None or new_target is None:
            return
        self.temp_targets[target.unique_id] = new_target.unique_id
        self.emit("retarget", target, {"new_target": new_target.unique_id})

    def devamp_cue(self, cue: Cue | None) -> None:
        if cue is None:
            return
        state = self.states.get(cue.unique_id)
        if state is None or state.plan is None or state.action_running == False:
            return
        whole = False
        if state.plan.is_looping(state.action_elapsed) == False:
            return
        position = state.plan.locate(state.action_elapsed)
        if position is not None and state.plan.segments[position["slice"]].count != INFINITE:
            whole = True
        state.plan.devamp(state.action_elapsed, whole_cue=whole)
        state.action_duration = state.plan.total_duration()
        self.emit("devamp", cue, {"whole_cue": whole})

    def _run_devamp(self, state: CueState) -> None:
        cue = state.cue
        target = self.resolve_target(cue)
        if target is None:
            return
        whole_cue = int(cue.params.get("devamp_type", 1)) == 2
        target_state = self.states.get(target.unique_id)
        if target_state is None or target_state.plan is None or target_state.action_running == False:
            return
        plan = target_state.plan
        if plan.is_looping(target_state.action_elapsed) == False:
            return
        end_of_iteration = plan.end_of_current_iteration(target_state.action_elapsed)
        plan.devamp(target_state.action_elapsed, whole_cue=whole_cue)
        target_state.action_duration = plan.total_duration()
        self.emit("devamp", target, {"whole_cue": whole_cue})
        start_next = cue.params.get("start_next_when_slice_ends", False) == True
        stop_target = cue.params.get("stop_target_when_slice_ends", False) == True
        if start_next == True and end_of_iteration is not None:
            wait = max(0.0, end_of_iteration - target_state.action_elapsed)
            state.devamp_watchers.append({"after": wait, "elapsed": 0.0, "stop_target": stop_target,
                                          "target": target.unique_id})
            # il Devamp resta in esecuzione fino al momento del passaggio
            state.action_duration = wait
            state.post_wait_total = wait

    # ------------------------------------------------------------------ script
    def compile_script(self, cue: Cue) -> str:
        source = str(cue.params.get("script_source", ""))
        try:
            compile(source, "<script cue>", "exec")
        except SyntaxError as problem:
            cue.params["compile_error"] = "riga %s: %s" % (problem.lineno, problem.msg)
            return cue.params["compile_error"]
        cue.params["compile_error"] = ""
        return ""

    def _run_script(self, state: CueState) -> None:
        cue = state.cue
        source = str(cue.params.get("script_source", ""))
        api = ScriptApi(self, self.script_output)
        scope = {"__builtins__": _safe_builtins(), "api": api, "workspace": self.workspace, "cue": api.cue,
                 "go": api.go, "log": api.log, "this_cue": ScriptCue(self, cue)}
        try:
            exec(compile(source, "<script cue>", "exec"), scope)
        except Exception as problem:
            state.error = repr(problem)
            self.emit("script_error", cue, {"error": state.error})

    # ------------------------------------------------------------------ fade
    def fade_parameters(self, cue: Cue) -> list[str]:
        names = []
        params = cue.params
        if params.get("do_opacity", False) == True:
            names.append("opacity")
        if params.get("do_rate", False) == True:
            names.append("rate")
        if params.get("do_translation", False) == True:
            names.append("translation")
        if params.get("do_scale", False) == True:
            names.append("scale")
        if params.get("do_rotation", False) == True:
            names.append("rotation")
        for key in params.get("levels", {}):
            names.append("level:" + str(key))
        if len(params.get("fx_states", {})) > 0:
            names.append("fx")
        if params.get("targets_light", False) == True:
            names.append("light")
        return names

    def _fade_targets(self, cue: Cue) -> list[Cue]:
        target = self.resolve_target(cue)
        if target is None:
            return []
        if target.is_group_like() == False:
            return [target]
        result = []
        for node in target.walk():
            if node is target:
                continue
            if node.cue_type in (TYPE_AUDIO, TYPE_VIDEO, TYPE_MIC, TYPE_CAMERA, TYPE_TEXT):
                found = self.states.get(node.unique_id)
                if found is not None and found.is_active() == True:
                    result.append(node)
        return result

    def _start_fade(self, state: CueState) -> None:
        cue = state.cue
        relative = cue.params.get("levels_mode", "absolute") == "relative"
        geometry_relative = cue.params.get("geometry_mode", "absolute") == "relative"
        entries = []
        for target in self._fade_targets(cue):
            snapshot = self._fade_snapshots.setdefault(cue.unique_id, {})
            for name in self.fade_parameters(cue):
                begin = self._current_value(target, name)
                end = self._fade_end_value(cue, target, name, begin, relative, geometry_relative)
                if begin is None or end is None:
                    continue
                entries.append({"target": target.unique_id, "name": name, "begin": begin, "end": end})
                snapshot.setdefault(target.unique_id + "|" + name, {"begin": begin, "end": end})
        if cue.params.get("do_rate", False) == True:
            pass
        state.fade_data = {"entries": entries, "domain": cue.params.get("audio_domain", "decibel")}
        if state.action_duration <= EPSILON:
            self._apply_fade(state, 1.0)

    def _current_value(self, target: Cue, name: str):
        if name.startswith("level:"):
            key = name[len("level:"):]
            levels = self.get_param(target, "levels", {})
            return float(levels.get(key, 0.0 if key == "main" else MINUS_INFINITY))
        if name == "opacity":
            return float(self.get_param(target, "opacity", 1.0))
        if name == "rate":
            return float(self.get_param(target, "rate", 1.0))
        if name in ("translation", "scale"):
            return list(self.get_param(target, name, [0.0, 0.0] if name == "translation" else [1.0, 1.0]))
        if name == "rotation":
            return list(self.get_param(target, "quaternion", [1.0, 0.0, 0.0, 0.0]))
        if name == "fx":
            return dict(self.get_param(target, "fx_states", {}))
        if name == "light":
            return 0.0
        return None

    def _fade_end_value(self, cue: Cue, target: Cue, name: str, begin, relative: bool, geometry_relative: bool):
        params = cue.params
        maximum = float(self.workspace.settings.get("max_volume", 12.0))
        if name.startswith("level:"):
            wanted = float(params["levels"][name[len("level:"):]])
            if relative == True:
                wanted = wanted if begin == MINUS_INFINITY else begin + wanted
            if wanted > maximum:
                wanted = maximum
            return wanted
        if name == "opacity":
            wanted = float(params.get("opacity", 1.0))
            return begin + wanted if geometry_relative == True else wanted
        if name == "rate":
            wanted = float(params.get("rate", 1.0))
            return max(0.03, min(33.0, begin * wanted if geometry_relative == True else wanted))
        if name in ("translation", "scale"):
            wanted = list(params.get(name, begin))
            if geometry_relative == True:
                if name == "translation":
                    return [begin[0] + wanted[0], begin[1] + wanted[1]]
                return [begin[0] * wanted[0], begin[1] * wanted[1]]
            return wanted
        if name == "rotation":
            return list(params.get("quaternion", begin))
        if name == "fx":
            return dict(params.get("fx_states", {}))
        if name == "light":
            return 1.0
        return None

    def _apply_fade(self, state: CueState, position: float) -> None:
        cue = state.cue
        curve = cue.params.get("curve")
        domain = state.fade_data["domain"]
        for entry in state.fade_data["entries"]:
            target = self.workspace.find_by_id(entry["target"])
            if target is None:
                continue
            name = entry["name"]
            begin = entry["begin"]
            end = entry["end"]
            if name.startswith("level:"):
                value = self._interpolate_level(begin, end, position, curve, domain)
                levels = dict(self.get_param(target, "levels", {}))
                levels[name[len("level:"):]] = value
                self.set_live_param(target, "levels", levels)
            elif name in ("opacity", "rate"):
                self.set_live_param(target, name, curves.interpolate(begin, end, position, curve))
            elif name in ("translation", "scale"):
                values = [curves.interpolate(begin[index], end[index], position, curve) for index in range(2)]
                self.set_live_param(target, name, values)
            elif name == "rotation":
                shaped = curves.evaluate(curve, position, True) if position < 1.0 else 1.0
                self.set_live_param(target, "quaternion", curves.slerp(begin, end, shaped))
            elif name == "fx":
                if position >= 1.0:
                    self.set_live_param(target, "fx_states", end)
            elif name == "light" and self.light_bridge is not None:
                self.light_bridge.fade_light(self, state, position)

    def _interpolate_level(self, begin: float, end: float, position: float, curve, domain: str) -> float:
        if position >= 1.0:
            return end
        if domain == "linear":
            start_linear = db_to_linear(begin)
            end_linear = db_to_linear(end)
            return linear_to_db(curves.interpolate(start_linear, end_linear, position, curve))
        floor = float(self.workspace.settings.get("min_volume", -60.0))
        start_value = floor if begin == MINUS_INFINITY else begin
        end_value = floor if end == MINUS_INFINITY else end
        value = curves.interpolate(start_value, end_value, position, curve)
        if end == MINUS_INFINITY and value <= floor:
            return MINUS_INFINITY
        return value

    def _finish_fade(self, state: CueState, completed: bool) -> None:
        cue = state.cue
        if completed == True and state.fade_data is not None:
            self._apply_fade(state, 1.0)
            if cue.params.get("stop_target_when_done", False) == True:
                for target in self._fade_targets(cue):
                    self.stop_cue(target)
                target = self.resolve_target(cue)
                if target is not None:
                    self.stop_cue(target)
        state.fade_data = None

    def revert_fade(self, cue: Cue) -> None:
        """Ripristina solo i parametri toccati dal Fade e non modificati poi da altri."""
        snapshot = self._fade_snapshots.get(cue.unique_id, {})
        for key, values in snapshot.items():
            identifier, name = key.split("|", 1)
            target = self.workspace.find_by_id(identifier)
            if target is None:
                continue
            current = self._current_value(target, name)
            if name == "rotation" or isinstance(current, list):
                unchanged = _close_list(current, values["end"])
            elif isinstance(current, dict):
                unchanged = current == values["end"]
            else:
                unchanged = current is not None and abs(float(current) - float(values["end"])) < 1e-6 or (
                    current == values["end"])
            if unchanged == False:
                continue
            if name.startswith("level:"):
                levels = dict(self.get_param(target, "levels", {}))
                levels[name[len("level:"):]] = values["begin"]
                self.set_live_param(target, "levels", levels)
            elif name == "rotation":
                self.set_live_param(target, "quaternion", values["begin"])
            elif name == "fx":
                self.set_live_param(target, "fx_states", values["begin"])
            else:
                self.set_live_param(target, name, values["begin"])
        self._fade_snapshots.pop(cue.unique_id, None)

    # ------------------------------------------------------------------ avanzamento del tempo
    def update(self) -> None:
        with self.lock:
            now = self.clock.now()
            delta = now - self._last_time
            self._last_time = now
            if delta > 0:
                self._advance_internal(delta)

    def advance(self, delta: float) -> None:
        """Con ManualClock fa avanzare l'orologio e il motore insieme (usato dai test)."""
        if isinstance(self.clock, ManualClock):
            self.clock.advance(delta)
            self._last_time = self.clock.now()
        self._advance_internal(delta)

    def _advance_internal(self, delta: float) -> None:
        remaining = float(delta)
        guard = 0
        while guard < 1000000:
            guard = guard + 1
            self._process_due()
            if remaining <= EPSILON:
                break
            step = min(remaining, self._time_to_next_event())
            if step <= 0:
                step = min(remaining, 1e-6)
            self._elapse(step)
            remaining = remaining - step
        self._process_due()
        self._update_actions()
        self._prune()

    def _time_to_next_event(self) -> float:
        best = math.inf
        for state in self.states.values():
            if state.paused == True:
                continue
            if state.pre_wait_running == True:
                best = min(best, state.pre_wait_total - state.pre_wait_elapsed)
            if state.action_running == True:
                if state.action_duration != INFINITE:
                    best = min(best, state.action_duration - state.action_elapsed)
                if state.follow_at is not None and state.followed == False:
                    best = min(best, state.follow_at - state.action_elapsed)
                for watcher in state.devamp_watchers:
                    best = min(best, watcher["after"] - watcher["elapsed"])
            if state.post_wait_running == True:
                best = min(best, state.post_wait_total - state.post_wait_elapsed)
            if state.fade_out is not None:
                best = min(best, state.fade_out["time"] - state.fade_out["elapsed"])
            if state.panicking == True:
                best = min(best, float(self.workspace.settings.get("panic_duration", 2.0)) - state.panic_elapsed)
        return max(0.0, best)

    def _elapse(self, step: float) -> None:
        for state in list(self.states.values()):
            if state.paused == True:
                continue
            if state.pre_wait_running == True:
                state.pre_wait_elapsed = state.pre_wait_elapsed + step
            if state.action_running == True:
                state.action_elapsed = state.action_elapsed + step
                for watcher in state.devamp_watchers:
                    watcher["elapsed"] = watcher["elapsed"] + step
            if state.post_wait_running == True:
                state.post_wait_elapsed = state.post_wait_elapsed + step
            if state.fade_out is not None:
                state.fade_out["elapsed"] = state.fade_out["elapsed"] + step
                fraction = min(1.0, state.fade_out["elapsed"] / max(state.fade_out["time"], EPSILON))
                self.gains[state.cue.unique_id] = max(0.0, 1.0 - fraction)
            if state.panicking == True:
                state.panic_elapsed = state.panic_elapsed + step

    def _process_due(self) -> None:
        guard = 0
        while guard < 100000:
            guard = guard + 1
            if self._process_one_due() == False:
                break

    def _process_one_due(self) -> bool:
        for state in list(self.states.values()):
            if state.paused == True or state.is_active() == False:
                continue
            cue = state.cue
            if state.panicking == True:
                if state.panic_elapsed >= float(self.workspace.settings.get("panic_duration", 2.0)) - EPSILON:
                    self._terminate_state(state, True)
                    return True
            if state.fade_out is not None and state.fade_out["elapsed"] >= state.fade_out["time"] - EPSILON:
                self._terminate_state(state, True)
                return True
            if state.pre_wait_running == True and state.pre_wait_elapsed >= state.pre_wait_total - EPSILON:
                self._begin_action(state)
                return True
            if state.action_running == True:
                for watcher in list(state.devamp_watchers):
                    if watcher["elapsed"] >= watcher["after"] - EPSILON:
                        state.devamp_watchers.remove(watcher)
                        self._complete_devamp_handoff(state, watcher)
                        return True
                if state.follow_at is not None and state.followed == False and \
                        state.action_elapsed >= state.follow_at - EPSILON:
                    state.followed = True
                    state.crossfading_out = True
                    following = self.next_sibling(cue)
                    if following is not None:
                        self.emit("crossfade", cue, {"duration": state.action_duration - state.follow_at})
                        self.start_cue(following, origin=ORIGIN_CONTINUE)
                    return True
                if cue.is_group_like() == True and state.group_started == True:
                    if self._group_has_active_descendants(cue) == False and self._group_is_idle(state) == True:
                        self._finish_action(state)
                        return True
                elif state.action_duration != INFINITE and state.action_elapsed >= state.action_duration - EPSILON:
                    self._finish_action(state)
                    return True
            if state.post_wait_running == True and state.post_wait_elapsed >= state.post_wait_total - EPSILON:
                state.post_wait_running = False
                self.emit("post_wait_end", cue, {})
                if self.effective_continue(cue) == CONTINUE_AUTO_CONTINUE and state.preview == False:
                    following = self.next_sibling(cue)
                    if following is not None:
                        self.start_cue(following, origin=ORIGIN_CONTINUE)
                return True
        return False

    def _group_is_idle(self, state: CueState) -> bool:
        return state.pre_wait_running == False

    def _complete_devamp_handoff(self, state: CueState, watcher: dict) -> None:
        if watcher["stop_target"] == True:
            target = self.workspace.find_by_id(watcher["target"])
            self.stop_cue(target)
        following = self.next_sibling(state.cue)
        if following is not None and state.preview == False:
            self.start_cue(following, origin=ORIGIN_CONTINUE)
        state.post_wait_running = False

    def _finish_action(self, state: CueState) -> None:
        cue = state.cue
        state.action_running = False
        if state.fade_data is not None:
            self._finish_fade(state, completed=True)
        self._release_duck(cue)
        self.emit("action_end", cue, {})
        if state.preview == False and state.followed == False:
            if self.effective_continue(cue) == CONTINUE_AUTO_FOLLOW:
                following = self.next_sibling(cue)
                if following is not None:
                    self.start_cue(following, origin=ORIGIN_CONTINUE)
        handler = self._handler(cue)
        if handler is not None and state.virtual == False:
            handler.stop(self, state, False)

    def _update_actions(self) -> None:
        for state in list(self.states.values()):
            if state.paused == True or state.action_running == False:
                continue
            if state.fade_data is not None and state.action_duration > 0:
                fraction = min(1.0, state.action_elapsed / state.action_duration)
                self._apply_fade(state, fraction)
            handler = self._handler(state.cue)
            if handler is not None and state.virtual == False:
                handler.update(self, state)

    def _prune(self) -> None:
        for identifier in [key for key, state in self.states.items() if state.is_active() == False]:
            del self.states[identifier]

    # ------------------------------------------------------------------ informazioni per UI/OSC
    def status(self, cue: Cue) -> dict:
        state = self.states.get(cue.unique_id)
        info = {"loaded": cue.unique_id in self.loaded, "running": False, "pre_wait_running": False,
                "post_wait_running": False, "paused": False, "tailing_out": False, "panicking": False,
                "crossfading_out": False, "broken": self.broken_reason(cue) != "", "armed": cue.armed,
                "pre_wait_elapsed": 0.0, "action_elapsed": 0.0, "post_wait_elapsed": 0.0,
                "action_duration": 0.0, "broken_reason": self.broken_reason(cue)}
        if state is not None:
            info.update({"running": state.action_running, "pre_wait_running": state.pre_wait_running,
                         "post_wait_running": state.post_wait_running, "paused": state.paused,
                         "panicking": state.panicking, "crossfading_out": state.crossfading_out,
                         "pre_wait_elapsed": state.pre_wait_elapsed, "action_elapsed": state.action_elapsed,
                         "post_wait_elapsed": state.post_wait_elapsed, "action_duration": state.action_duration})
        return info

    def current_color(self, cue: Cue) -> str:
        if cue.color == "none":
            return "none"
        if cue.color_condition == "before_action":
            return cue.color if cue.unique_id not in self.fired else "none"
        if cue.color_condition == "after_action":
            return cue.color if cue.unique_id in self.fired else "none"
        return cue.color

    def active_cues(self) -> list[Cue]:
        return [state.cue for state in self.states.values() if state.is_active()]


def _close_list(first, second) -> bool:
    if len(first) != len(second):
        return False
    for index in range(len(first)):
        if abs(float(first[index]) - float(second[index])) > 1e-6:
            return False
    return True
