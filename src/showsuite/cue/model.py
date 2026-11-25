"""Modello dati della sezione Cue: Cue, Workspace, impostazioni, persistenza JSON (*.showcue)."""
from __future__ import annotations

import copy
import json
import os
import uuid

from .curves import default_curve

SCHEMA_VERSION = 1

TYPE_AUDIO = "audio"
TYPE_MIC = "mic"
TYPE_VIDEO = "video"
TYPE_CAMERA = "camera"
TYPE_TEXT = "text"
TYPE_LIGHT = "light"
TYPE_FADE = "fade"
TYPE_NETWORK = "network"
TYPE_MIDI = "midi"
TYPE_MIDI_FILE = "midi file"
TYPE_TIMECODE = "timecode"
TYPE_GROUP = "group"
TYPE_START = "start"
TYPE_STOP = "stop"
TYPE_PAUSE = "pause"
TYPE_LOAD = "load"
TYPE_RESET = "reset"
TYPE_DEVAMP = "devamp"
TYPE_GOTO = "goto"
TYPE_TARGET = "target"
TYPE_ARM = "arm"
TYPE_DISARM = "disarm"
TYPE_WAIT = "wait"
TYPE_MEMO = "memo"
TYPE_SCRIPT = "script"
TYPE_LIST = "list"
TYPE_CART = "cart"

CUE_TYPES = [TYPE_AUDIO, TYPE_MIC, TYPE_VIDEO, TYPE_CAMERA, TYPE_TEXT, TYPE_LIGHT, TYPE_FADE, TYPE_NETWORK, TYPE_MIDI,
             TYPE_MIDI_FILE, TYPE_TIMECODE, TYPE_GROUP, TYPE_START, TYPE_STOP, TYPE_PAUSE, TYPE_LOAD, TYPE_RESET,
             TYPE_DEVAMP, TYPE_GOTO, TYPE_TARGET, TYPE_ARM, TYPE_DISARM, TYPE_WAIT, TYPE_MEMO, TYPE_SCRIPT]
CONTAINER_TYPES = [TYPE_LIST, TYPE_CART]

# tipi che richiedono un target che è un altro cue
CUE_TARGET_TYPES = [TYPE_FADE, TYPE_START, TYPE_STOP, TYPE_PAUSE, TYPE_LOAD, TYPE_RESET, TYPE_DEVAMP, TYPE_GOTO,
                    TYPE_TARGET, TYPE_ARM, TYPE_DISARM]
# tipi con un file come target
FILE_TARGET_TYPES = [TYPE_AUDIO, TYPE_VIDEO, TYPE_MIDI_FILE]
# tipi che producono audio
AUDIO_TYPES = [TYPE_AUDIO, TYPE_MIC, TYPE_VIDEO, TYPE_CAMERA]
# tipi con uscita video
VIDEO_TYPES = [TYPE_VIDEO, TYPE_CAMERA, TYPE_TEXT]
# tipi istantanei: nessuna durata modificabile
INSTANT_TYPES = [TYPE_PAUSE, TYPE_START, TYPE_STOP, TYPE_LOAD, TYPE_RESET, TYPE_GOTO, TYPE_TARGET, TYPE_ARM,
                 TYPE_DISARM, TYPE_MEMO, TYPE_SCRIPT, TYPE_DEVAMP]

GROUP_LIST = 0
GROUP_START_FIRST_AND_ENTER = 1
GROUP_START_FIRST = 2
GROUP_TIMELINE = 3
GROUP_START_RANDOM = 4
GROUP_CART = 5
GROUP_PLAYLIST = 6

CONTINUE_NONE = 0
CONTINUE_AUTO_CONTINUE = 1
CONTINUE_AUTO_FOLLOW = 2

COLORS = ["none", "red", "orange", "green", "blue", "purple"]
FORBIDDEN_NUMBER_CHARACTERS = " #*,/?[]{}"


class DuplicateNumberError(ValueError):
    pass


class InvalidNumberError(ValueError):
    pass


def new_unique_id() -> str:
    return str(uuid.uuid4()).upper()


def geometry_defaults() -> dict:
    return {"fill_stage": True, "preserve_aspect_ratio": True, "opacity": 1.0, "smooth": True, "layer": 0,
            "blend_mode": "normal", "video_fx": [], "crop": [0.0, 0.0, 0.0, 0.0], "translation": [0.0, 0.0],
            "scale": [1.0, 1.0], "anchor": [0.0, 0.0], "quaternion": [1.0, 0.0, 0.0, 0.0], "hold_last_frame": False,
            "stage": 1}


def audio_defaults() -> dict:
    return {"audio_output_patch": 1, "audio_map": "", "objects": [], "levels": {}, "trim": 0.0, "audio_fx": [], "start_time": 0.0, "end_time": None,
            "play_count": 1, "infinite_loop": False, "slices": [], "rate": 1.0, "preserve_pitch": False,
            "integrated_fade": {"enabled": False, "curve": "custom", "lock_to_cue": False, "points": []},
            "media_duration": None, "media_channels": 2, "media_sample_rate": 48000, "mute": False, "solo": False}


def default_params(cue_type: str) -> dict:
    """Parametri specifici del tipo, con i default QLab."""
    params: dict = {}
    if cue_type == TYPE_AUDIO:
        params = {"file_target": ""}
        params.update(audio_defaults())
    elif cue_type == TYPE_MIC:
        params = {"audio_input_patch": 1, "channels": 1, "first_input": 1}
        params.update(audio_defaults())
    elif cue_type == TYPE_VIDEO:
        params = {"file_target": "", "clock": "video", "audio_track": 0}
        params.update(audio_defaults())
        params.update(geometry_defaults())
    elif cue_type == TYPE_CAMERA:
        params = {"video_input_patch": 1, "audio_input_patch": 1, "channels": 1, "first_input": 1}
        params.update(audio_defaults())
        params.update(geometry_defaults())
    elif cue_type == TYPE_TEXT:
        params = {"text": "", "fixed_width": 0, "format": {"font_family": "Sans", "font_size": 48.0, "bold": False,
                                                           "italic": False, "color": [1.0, 1.0, 1.0, 1.0],
                                                           "background_color": [0.0, 0.0, 0.0, 0.0],
                                                           "alignment": "center", "line_spacing": 1.0}}
        params.update(geometry_defaults())
    elif cue_type == TYPE_LIGHT:
        params = {"commands": [], "curve": default_curve(), "collate_previous": False, "subcontroller": False}
        params["curve"]["type"] = "custom"
    elif cue_type == TYPE_FADE:
        params = {"curve": default_curve(), "audio_domain": "decibel", "stop_target_when_done": False,
                  "levels_mode": "absolute", "geometry_mode": "absolute", "levels": {}, "do_opacity": False,
                  "opacity": 1.0, "do_rate": False, "rate": 1.0, "do_translation": False, "translation": [0.0, 0.0],
                  "do_scale": False, "scale": [1.0, 1.0], "do_rotation": False, "rotation": 0.0,
                  "rotation_type": 0, "quaternion": [1.0, 0.0, 0.0, 0.0], "fx_states": {}, "live_preview": True,
                  "targets_light": False}
    elif cue_type == TYPE_NETWORK:
        params = {"network_patch": 1, "message_kind": "osc", "message": "", "fade_type": 0, "number_type": 1,
                  "fade_from": 0.0, "fade_to": 1.0, "fps": 30, "path_width": 100, "path_height": 100, "path": [],
                  "curve": default_curve(), "parameter_values": {}, "parameter_fades": {}}
    elif cue_type == TYPE_MIDI:
        params = {"midi_patch": 1, "message_type": 1, "status": 1, "channel": 1, "byte1": 60, "byte2": 64,
                  "end_value": None, "command_format": 1, "command": 1, "device_id": 0, "q_number": "",
                  "q_list": "", "q_path": "", "macro": 0, "control_number": 0, "control_value": 0,
                  "timecode": [0, 0, 0, 0, 0], "timecode_format": 1, "raw_string": "", "curve": default_curve()}
    elif cue_type == TYPE_MIDI_FILE:
        params = {"file_target": "", "midi_patch": 1, "playback_rate": 1.0, "media_duration": None}
    elif cue_type == TYPE_TIMECODE:
        params = {"kind": "mtc", "midi_patch": 1, "audio_output_patch": 1, "channel": 0, "format": 1,
                  "start_time": "00:00:00:00", "stop_after": None}
    elif cue_type == TYPE_GROUP:
        params = {"group_mode": GROUP_LIST, "playlist_loop": False, "playlist_shuffle": False,
                  "playlist_crossfade": False, "playlist_crossfade_duration": 0.05,
                  "crossfade_curve_out": default_curve(), "crossfade_curve_in": default_curve()}
    elif cue_type == TYPE_LOAD:
        params = {"load_time": 0.0}
    elif cue_type == TYPE_DEVAMP:
        params = {"devamp_type": 1, "start_next_when_slice_ends": False, "stop_target_when_slice_ends": False}
    elif cue_type == TYPE_TARGET:
        params = {"new_target_number": ""}
    elif cue_type == TYPE_SCRIPT:
        params = {"script_source": "", "separate_process": True, "compile_error": ""}
    elif cue_type == TYPE_LIST:
        params = {"timecode_sync": False, "timecode_sync_mode": 0, "timecode_device": "", "timecode_channel": 1,
                  "timecode_format": 1, "timecode_start_behavior": 0, "timecode_stop_behavior": 0,
                  "timecode_lookback_time": 5.0, "timecode_freewheel_time": 0.0}
    elif cue_type == TYPE_CART:
        params = {"rows": 4, "columns": 4, "timecode_sync": False, "timecode_sync_mode": 0, "timecode_device": "",
                  "timecode_channel": 1, "timecode_format": 1, "timecode_start_behavior": 0,
                  "timecode_stop_behavior": 0, "timecode_lookback_time": 5.0, "timecode_freewheel_time": 0.0}
    return params


class Cue:
    """Un cue (o una lista/cart, o un Group). I parametri specifici stanno in `params`."""

    def __init__(self, cue_type: str, unique_id: str | None = None):
        self.cue_type = cue_type
        self.unique_id = unique_id or new_unique_id()
        self.number = ""
        self.name = ""
        self.notes = ""
        self.color = "none"
        self.color_condition = "always"
        self.flagged = False
        self.armed = True
        self.auto_load = False
        self.continue_mode = CONTINUE_NONE
        self.pre_wait = 0.0
        self.duration = 0.0
        self.post_wait = 0.0
        self.target_id = ""
        self.target_number = ""
        self.triggers = {"hotkey": None, "midi": None, "wall_clock": None, "timecode": None}
        self.second_trigger_action = 0
        self.second_trigger_on_release = False
        self.fade_and_stop_others = {"mode": 0, "time": 0.0}
        self.duck_others = {"enabled": False, "level": -12.0, "time": 1.0}
        self.cart_row = 0
        self.cart_column = 0
        self.params = default_params(cue_type)
        self.children: list[Cue] = []
        self.parent: Cue | None = None
        if cue_type == TYPE_WAIT:
            self.duration = 1.0
        if cue_type == TYPE_FADE:
            self.duration = 5.0
        if cue_type == TYPE_TIMECODE:
            self.duration = 0.0

    # --- classificazione ---
    def is_container(self) -> bool:
        return self.cue_type in CONTAINER_TYPES

    def is_group_like(self) -> bool:
        return self.cue_type in (TYPE_GROUP, TYPE_LIST, TYPE_CART)

    def has_cue_target(self) -> bool:
        return self.cue_type in CUE_TARGET_TYPES

    def has_file_target(self) -> bool:
        return self.cue_type in FILE_TARGET_TYPES

    def allows_editing_duration(self) -> bool:
        if self.cue_type in INSTANT_TYPES:
            return False
        if self.cue_type in (TYPE_LIST, TYPE_CART, TYPE_GROUP):
            return False
        if self.cue_type in (TYPE_AUDIO, TYPE_VIDEO, TYPE_MIDI_FILE, TYPE_MIC, TYPE_CAMERA):
            return False
        if self.cue_type == TYPE_TEXT:
            return True
        return True

    def group_mode(self) -> int:
        if self.cue_type == TYPE_LIST:
            return GROUP_LIST
        if self.cue_type == TYPE_CART:
            return GROUP_CART
        if self.cue_type == TYPE_GROUP:
            return int(self.params.get("group_mode", GROUP_LIST))
        return -1

    # --- nomi ---
    def default_name(self, workspace: "Workspace | None" = None) -> str:
        cue_type = self.cue_type
        if cue_type in (TYPE_AUDIO, TYPE_VIDEO, TYPE_MIDI_FILE):
            path = self.params.get("file_target", "")
            return os.path.basename(path) if path != "" else ""
        if cue_type == TYPE_TEXT:
            return str(self.params.get("text", "")).replace("\n", " ")
        if cue_type == TYPE_LIGHT:
            commands = self.params.get("commands", [])
            if len(commands) == 1:
                return str(commands[0])
            if len(commands) > 1:
                return "fade %d lights" % len(commands)
            return ""
        if cue_type == TYPE_FADE:
            target_name = self._target_label(workspace)
            if self.params.get("stop_target_when_done", False) == True:
                return "fade and stop " + target_name
            return "fade " + target_name
        if cue_type == TYPE_NETWORK:
            return str(self.params.get("message", ""))
        if cue_type == TYPE_MIDI:
            return midi_message_name(self.params)
        if cue_type == TYPE_TIMECODE:
            return str(self.params.get("start_time", ""))
        if cue_type in (TYPE_START, TYPE_STOP, TYPE_PAUSE, TYPE_LOAD, TYPE_RESET, TYPE_GOTO, TYPE_ARM, TYPE_DISARM,
                        TYPE_DEVAMP, TYPE_TARGET):
            return (cue_type + " " + self._target_label(workspace)).strip()
        if cue_type == TYPE_WAIT:
            return "wait " + ("%g" % self.duration) + "s"
        if cue_type == TYPE_MIC:
            return "mic"
        if cue_type == TYPE_CAMERA:
            return "camera"
        if cue_type == TYPE_GROUP:
            return "group"
        if cue_type == TYPE_LIST:
            return "Main Cue List"
        if cue_type == TYPE_CART:
            return "Cue Cart"
        return cue_type

    def _target_label(self, workspace) -> str:
        if workspace is None:
            return ""
        target = workspace.find_target(self)
        if target is None:
            return ""
        return target.display_name(workspace)

    def display_name(self, workspace: "Workspace | None" = None) -> str:
        if self.name != "":
            return self.name
        return self.default_name(workspace)

    def list_name(self, workspace: "Workspace | None" = None) -> str:
        return self.display_name(workspace)

    def standby_display(self, workspace: "Workspace | None" = None) -> str:
        if self.number == "":
            return self.display_name(workspace)
        return self.number + " • " + self.display_name(workspace)

    # --- albero ---
    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def root_list(self) -> "Cue | None":
        node = self
        while node.parent is not None:
            node = node.parent
        return node if node.is_container() else None

    # --- serializzazione ---
    def to_dict(self) -> dict:
        data = {"unique_id": self.unique_id, "type": self.cue_type, "number": self.number, "name": self.name,
                "notes": self.notes, "color": self.color, "color_condition": self.color_condition,
                "flagged": self.flagged, "armed": self.armed, "auto_load": self.auto_load,
                "continue_mode": self.continue_mode, "pre_wait": self.pre_wait, "duration": self.duration,
                "post_wait": self.post_wait, "target_id": self.target_id, "target_number": self.target_number,
                "triggers": copy.deepcopy(self.triggers), "second_trigger_action": self.second_trigger_action,
                "second_trigger_on_release": self.second_trigger_on_release,
                "fade_and_stop_others": dict(self.fade_and_stop_others), "duck_others": dict(self.duck_others),
                "cart_row": self.cart_row, "cart_column": self.cart_column, "params": copy.deepcopy(self.params)}
        if len(self.children) > 0:
            data["children"] = [child.to_dict() for child in self.children]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Cue":
        cue = cls(data["type"], data.get("unique_id"))
        simple = ["number", "name", "notes", "color", "color_condition", "flagged", "armed", "auto_load",
                  "continue_mode", "pre_wait", "duration", "post_wait", "target_id", "target_number",
                  "second_trigger_action", "second_trigger_on_release", "cart_row", "cart_column"]
        for key in simple:
            if key in data:
                setattr(cue, key, data[key])
        cue.triggers.update(copy.deepcopy(data.get("triggers", {})))
        cue.fade_and_stop_others.update(data.get("fade_and_stop_others", {}))
        cue.duck_others.update(data.get("duck_others", {}))
        stored_params = copy.deepcopy(data.get("params", {}))
        cue.params.update(stored_params)
        for child_data in data.get("children", []):
            child = cls.from_dict(child_data)
            child.parent = cue
            cue.children.append(child)
        return cue


def midi_message_name(params: dict) -> str:
    message_type = int(params.get("message_type", 1))
    if message_type == 2:
        return "MSC " + str(params.get("command", ""))
    if message_type == 3:
        return "SysEx"
    names = ["Note Off", "Note On", "Key Pressure", "Control Change", "Program Change", "Channel Pressure",
             "Pitch Bend"]
    status = int(params.get("status", 1))
    if 0 <= status < len(names):
        return names[status]
    return "MIDI"


def default_settings() -> dict:
    return {"min_go_time": 0.0, "key_up": False, "panic_duration": 2.0, "auto_number": True, "auto_number_increment": 1,
            "auto_load_default": False, "lock_playhead_to_selection": False, "display_size": "medium",
            "max_volume": 12.0, "min_volume": -60.0, "start_cue_on_open": False, "prompt_cue_on_close": False,
            "copy_media": False, "autosave_seconds": 0, "always_audition": False, "show_mode": False,
            "osc_access": True, "osc_port": 53000, "osc_reply_port": 53001, "osc_plain_port": 53535,
            "passcodes": [{"passcode": "", "view": False, "edit": False, "control": False}],
            "midi_channel": 0, "use_msc": False, "msc_device_id": 0, "use_musical_midi": False,
            "keyboard_controls": default_keyboard_controls(), "musical_midi_controls": {}, "osc_controls": {},
            "audition": {"audio": "unchanged", "video": "unchanged", "midi": "unchanged", "mtc": "unchanged",
                         "ltc": "unchanged", "network": "unchanged", "light": "unchanged"},
            "overrides": {"dmxOutput": True, "midiInput": True, "midiOutput": True, "mscInput": True,
                          "mscOutput": True, "sysexInput": True, "sysexOutput": True, "networkExternalInput": True,
                          "networkExternalOutput": True, "networkLocalInput": True, "networkLocalOutput": True,
                          "timecodeInput": True, "timecodeOutput": True},
            "collaboration": {"allow": False, "ask_before_allowing": True, "restrict_view_in_show_mode": True,
                              "collaborators": []}}


def default_keyboard_controls() -> dict:
    return {"go": "Space", "preview": "V", "load": "L", "panic": "S", "pause": "P", "pause_all": "[",
            "resume_all": "]", "panic_all": "Escape", "edit_number": "N", "edit_name": "Q", "edit_notes": "O",
            "edit_target": "T", "edit_pre_wait": "E", "edit_duration": "D", "edit_post_wait": "W",
            "edit_continue": "C", "flag": "F"}


class Workspace:
    """Documento ShowSuite Cue: liste/cart, impostazioni, patch."""

    def __init__(self, name: str = "Workspace"):
        self.workspace_id = new_unique_id()
        self.name = name
        self.path = ""
        self.settings = default_settings()
        self.lists: list[Cue] = []
        self.patches = {"audio": [], "audio_input": [], "video_stage": [], "video_route": [], "midi": [], "network": [],
                        "audio_map": [], "light": {}}
        self.active_list_id = ""
        self.modified = False
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        first = self.new_list("Main Cue List")
        self.active_list_id = first.unique_id

    # --- ricerca ---
    def all_cues(self):
        for cue_list in self.lists:
            yield from cue_list.walk()

    def find_by_id(self, unique_id: str) -> Cue | None:
        for cue in self.all_cues():
            if cue.unique_id == unique_id:
                return cue
        return None

    def find_by_number(self, number: str) -> Cue | None:
        if number == "" or number is None:
            return None
        for cue in self.all_cues():
            if cue.number == number:
                return cue
        return None

    def find_list(self, key: str) -> Cue | None:
        for cue_list in self.lists:
            if cue_list.unique_id == key or cue_list.name == key or cue_list.number == key:
                return cue_list
        return None

    def find_target(self, cue: Cue) -> Cue | None:
        if cue.target_id != "":
            found = self.find_by_id(cue.target_id)
            if found is not None:
                return found
        if cue.target_number != "":
            return self.find_by_number(cue.target_number)
        return None

    def active_list(self) -> Cue:
        found = self.find_by_id(self.active_list_id)
        if found is None:
            return self.lists[0]
        return found

    # --- liste ---
    def new_list(self, name: str = "", cart: bool = False) -> Cue:
        container = Cue(TYPE_CART if cart == True else TYPE_LIST)
        container.name = name
        self.lists.append(container)
        self.modified = True
        return container

    def delete_list(self, container: Cue) -> None:
        if len(self.lists) <= 1:
            raise ValueError("deve esistere almeno una lista")
        self.lists.remove(container)
        if self.active_list_id == container.unique_id:
            self.active_list_id = self.lists[0].unique_id
        self.modified = True

    # --- numerazione ---
    @staticmethod
    def validate_number(number: str) -> None:
        for character in number:
            if character in FORBIDDEN_NUMBER_CHARACTERS:
                raise InvalidNumberError("carattere non ammesso nel numero: " + repr(character))

    def number_in_use(self, number: str, ignore: Cue | None = None) -> bool:
        if number == "":
            return False
        for cue in self.all_cues():
            if cue is not ignore and cue.number == number:
                return True
        return False

    def set_number(self, cue: Cue, number: str) -> None:
        number = str(number)
        if number != "":
            self.validate_number(number)
            if self.number_in_use(number, ignore=cue) == True:
                raise DuplicateNumberError("numero già usato: " + number)
        cue.number = number
        self.modified = True

    def next_auto_number(self, parent: Cue, index: int) -> str:
        increment = int(self.settings.get("auto_number_increment", 1))
        previous_value = None
        next_value = None
        for position in range(index - 1, -1, -1):
            previous_value = _numeric(parent.children[position].number)
            if previous_value is not None:
                break
        for position in range(index, len(parent.children)):
            next_value = _numeric(parent.children[position].number)
            if next_value is not None:
                break
        if previous_value is None and next_value is None:
            candidate = float(increment)
        elif next_value is None:
            candidate = float(int(previous_value)) + increment
        elif previous_value is None:
            candidate = max(next_value - increment, 0.0)
        else:
            whole = float(int(previous_value)) + 1.0
            if whole < next_value:
                candidate = whole
            else:
                candidate = (previous_value + next_value) / 2.0
        text = _format_number(candidate)
        attempts = 0
        while self.number_in_use(text) == True and attempts < 1000:
            candidate = candidate + 1.0
            text = _format_number(candidate)
            attempts = attempts + 1
        return text

    def renumber(self, cues: list[Cue], start: float, increment: float, prefix: str = "", suffix: str = "") -> None:
        value = start
        for cue in cues:
            text = prefix + _format_number(value) + suffix
            while self.number_in_use(text, ignore=cue) == True:
                value = value + increment
                text = prefix + _format_number(value) + suffix
            cue.number = text
            value = value + increment
        self.modified = True

    def delete_numbers(self, cues: list[Cue]) -> None:
        for cue in cues:
            cue.number = ""
        self.modified = True

    # --- creazione/modifica ---
    def new_cue(self, cue_type: str, parent: Cue | None = None, index: int | None = None, number: str | None = None,
                auto_number: bool | None = None, name: str = "") -> Cue:
        if parent is None:
            parent = self.active_list()
        if parent.cue_type == TYPE_CART and cue_type == TYPE_GROUP:
            raise ValueError("un Cart non può contenere Group")
        if parent.is_group_like() == False:
            raise ValueError("il genitore deve essere un Group, una lista o un Cart")
        cue = Cue(cue_type)
        cue.name = name
        cue.auto_load = bool(self.settings.get("auto_load_default", False))
        if index is None or index > len(parent.children):
            index = len(parent.children)
        if number is not None:
            self.set_number(cue, number)
        else:
            use_auto = self.settings.get("auto_number", True) if auto_number is None else auto_number
            if use_auto == True and cue_type != TYPE_MEMO or (use_auto == True and cue_type == TYPE_MEMO):
                cue.number = self.next_auto_number(parent, index)
        cue.parent = parent
        parent.children.insert(index, cue)
        if parent.cue_type == TYPE_CART:
            cue.cart_row, cue.cart_column = self.first_free_cart_cell(parent)
        if cue_type == TYPE_GROUP and parent.cue_type == TYPE_LIST:
            pass
        self.modified = True
        return cue

    def first_free_cart_cell(self, cart: Cue) -> tuple[int, int]:
        rows = int(cart.params["rows"])
        columns = int(cart.params["columns"])
        used = set()
        for child in cart.children:
            used.add((child.cart_row, child.cart_column))
        for row in range(1, rows + 1):
            for column in range(1, columns + 1):
                if (row, column) not in used:
                    return row, column
        cart.params["rows"] = rows + 1
        return rows + 1, 1

    def set_cart_size(self, cart: Cue, rows: int, columns: int) -> None:
        rows = int(max(1, min(10, rows)))
        columns = int(max(1, min(10, columns)))
        for child in cart.children:
            if child.cart_row > rows or child.cart_column > columns:
                raise ValueError("il cart non può ridursi sotto l'ingombro dei cue")
        cart.params["rows"] = rows
        cart.params["columns"] = columns
        self.modified = True

    def delete_cue(self, cue: Cue) -> None:
        if cue.parent is None:
            raise ValueError("per eliminare una lista usare delete_list")
        cue.parent.children.remove(cue)
        parent = cue.parent
        cue.parent = None
        del parent
        self.modified = True

    def move_cue(self, cue: Cue, new_parent: Cue, index: int | None = None) -> None:
        if cue.parent is None:
            raise ValueError("liste e cart non si spostano")
        node = new_parent
        while node is not None:
            if node is cue:
                raise ValueError("impossibile spostare un Group dentro se stesso")
            node = node.parent
        if new_parent.cue_type == TYPE_CART and cue.cue_type == TYPE_GROUP:
            raise ValueError("un Cart non può contenere Group")
        old_parent = cue.parent
        old_parent.children.remove(cue)
        if index is None or index > len(new_parent.children):
            index = len(new_parent.children)
        new_parent.children.insert(index, cue)
        cue.parent = new_parent
        if new_parent.cue_type == TYPE_CART:
            cue.cart_row, cue.cart_column = self.first_free_cart_cell(new_parent)
        self.modified = True

    def make_group(self, cues: list[Cue], mode: int = GROUP_LIST) -> Cue:
        """Crea un Group che contiene i cue indicati (stesso genitore), nella posizione del primo."""
        if len(cues) == 0:
            raise ValueError("nessun cue")
        parent = cues[0].parent
        for cue in cues:
            if cue.parent is not parent:
                raise ValueError("i cue devono avere lo stesso genitore")
        ordered = sorted(cues, key=lambda cue: parent.children.index(cue))
        position = parent.children.index(ordered[0])
        group = self.new_cue(TYPE_GROUP, parent=parent, index=position)
        group.params["group_mode"] = mode
        for cue in ordered:
            self.move_cue(cue, group)
        return group

    def duplicate_cue(self, cue: Cue) -> Cue:
        data = cue.to_dict()
        copy_cue = _clone_with_new_ids(data)
        for node in copy_cue.walk():
            node.number = ""
        parent = cue.parent
        index = parent.children.index(cue) + 1
        copy_cue.parent = parent
        parent.children.insert(index, copy_cue)
        self.modified = True
        return copy_cue

    # --- undo (snapshot) ---
    def push_undo(self) -> None:
        self._undo_stack.append(json.dumps(self.to_dict()))
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> bool:
        if len(self._undo_stack) == 0:
            return False
        self._redo_stack.append(json.dumps(self.to_dict()))
        self._restore(json.loads(self._undo_stack.pop()))
        return True

    def redo(self) -> bool:
        if len(self._redo_stack) == 0:
            return False
        self._undo_stack.append(json.dumps(self.to_dict()))
        self._restore(json.loads(self._redo_stack.pop()))
        return True

    def _restore(self, data: dict) -> None:
        self.settings = data["settings"]
        self.patches = data["patches"]
        self.lists = []
        for list_data in data["lists"]:
            self.lists.append(Cue.from_dict(list_data))
        self.active_list_id = data.get("active_list_id", self.lists[0].unique_id)
        self.modified = True

    # --- persistenza ---
    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, "workspace_id": self.workspace_id, "name": self.name,
                "active_list_id": self.active_list_id, "settings": copy.deepcopy(self.settings),
                "patches": copy.deepcopy(self.patches), "lists": [cue_list.to_dict() for cue_list in self.lists]}

    @classmethod
    def from_dict(cls, data: dict) -> "Workspace":
        data = migrate(data)
        workspace = cls(data.get("name", "Workspace"))
        workspace.workspace_id = data.get("workspace_id", workspace.workspace_id)
        workspace.settings = default_settings()
        stored_settings = copy.deepcopy(data.get("settings", {}))
        workspace.settings.update(stored_settings)
        workspace.patches.update(copy.deepcopy(data.get("patches", {})))
        workspace.lists = [Cue.from_dict(list_data) for list_data in data.get("lists", [])]
        if len(workspace.lists) == 0:
            workspace.new_list("Main Cue List")
        workspace.active_list_id = data.get("active_list_id", workspace.lists[0].unique_id)
        workspace.modified = False
        return workspace

    def save(self, path: str | None = None) -> None:
        if path is not None:
            self.path = path
        if self.path == "":
            raise ValueError("percorso mancante")
        temporary_path = self.path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=1, ensure_ascii=False)
        os.replace(temporary_path, self.path)
        self.modified = False

    @classmethod
    def load(cls, path: str) -> "Workspace":
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        workspace = cls.from_dict(data)
        workspace.path = path
        return workspace


def migrate(data: dict) -> dict:
    """Migrazioni di schema: per ora esiste solo la versione 1."""
    version = int(data.get("schema_version", 1))
    if version > SCHEMA_VERSION:
        raise ValueError("file creato da una versione più recente di ShowSuite")
    return data


def _clone_with_new_ids(data: dict) -> Cue:
    cue = Cue.from_dict(data)
    for node in cue.walk():
        node.unique_id = new_unique_id()
    return cue


def _numeric(number: str):
    try:
        return float(number)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    text = ("%.6f" % value).rstrip("0")
    return text
