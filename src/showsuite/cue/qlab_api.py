"""API OSC compatibile con QLab 5 (indirizzi, permessi, risposte JSON, wildcard, +/-, /live, push /update).

`QLabApi.handle(address, args, client)` è indipendente dal trasporto: usa `ClientHandle.send` per le risposte.
Vedi specs/SPEC-osc-qlab.md. Parti NON implementate sono elencate in `NOT_IMPLEMENTED`."""
from __future__ import annotations

import json
import re
import time

from .engine import ORIGIN_OSC, Runtime
from .model import (COLORS, CUE_TYPES, TYPE_CART, TYPE_LIST, TYPE_GROUP, Cue, DuplicateNumberError,
                    InvalidNumberError)
from .osc import Impulse, has_wildcard, pattern_matches
from .playback import INFINITE

SESSION_TIMEOUT = 61.0
API_VERSION = "5.0.0-showsuite"

NOT_IMPLEMENTED = ["tempDuration", "liveAverageLevel", "fontNames/fontFamiliesAndStyles", "text/format/* per range",
                   "video/* settings per route/stage/region (solo lettura di patches)", "mDNS/Bonjour (opzionale)",
                   "soloCueInTime", "isOverridden (sempre false)"]

TYPE_NAMES = {"audio": "Audio", "mic": "Mic", "video": "Video", "camera": "Camera", "text": "Text", "light": "Light",
              "fade": "Fade", "network": "Network", "midi": "MIDI", "midi file": "MIDI File",
              "timecode": "Timecode", "group": "Group", "start": "Start", "stop": "Stop", "pause": "Pause",
              "load": "Load", "reset": "Reset", "devamp": "Devamp", "goto": "GoTo", "target": "Target",
              "arm": "Arm", "disarm": "Disarm", "wait": "Wait", "memo": "Memo", "script": "Script",
              "list": "Cue List", "cart": "Cart"}
NEW_TYPE_ALIASES = {"list": TYPE_LIST, "cuelist": TYPE_LIST, "cue list": TYPE_LIST, "cart": TYPE_CART,
                    "cuecart": TYPE_CART, "cue cart": TYPE_CART, "midifile": "midi file"}
COLOR_CONDITIONS = ["always", "before_action", "after_action"]
GEO_MODES = ["absolute", "relative"]


class ApiError(Exception):
    def __init__(self, message: str, status: str = "error"):
        super().__init__(message)
        self.status = status


def to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, Impulse):
        return True
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip()
    if text == "":
        return False
    return text[0] not in "NnFf0"


def to_float(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        raise ApiError("valore numerico non valido: " + str(value))


def to_int(value) -> int:
    return int(round(to_float(value)))


CONVERTERS = {"str": lambda value: str(value), "bool": to_bool, "float": to_float, "int": to_int,
              "json": lambda value: json.loads(value) if isinstance(value, str) else value}

# nome OSC -> (chiave in params, tipo)
PARAM_PROPS = {
    "startTime": ("start_time", "float"), "endTime": ("end_time", "float"), "playCount": ("play_count", "int"),
    "infiniteLoop": ("infinite_loop", "bool"), "rate": ("rate", "float"), "preservePitch": ("preserve_pitch", "bool"),
    "lockFadeToCue": ("lock_to_cue", "bool"), "fillStage": ("fill_stage", "bool"),
    "preserveAspectRatio": ("preserve_aspect_ratio", "bool"), "opacity": ("opacity", "float"),
    "layer": ("layer", "int"), "smooth": ("smooth", "bool"), "blendMode": ("blend_mode", "str"),
    "holdLastFrame": ("hold_last_frame", "bool"), "clockType": ("clock", "str"), "stage": ("stage", "int"),
    "text": ("text", "str"), "fixedWidth": ("fixed_width", "int"), "doOpacity": ("do_opacity", "bool"),
    "doRate": ("do_rate", "bool"), "doRotation": ("do_rotation", "bool"), "doScale": ("do_scale", "bool"),
    "doTranslation": ("do_translation", "bool"), "rotationType": ("rotation_type", "int"),
    "rotation": ("rotation", "float"), "stopTargetWhenDone": ("stop_target_when_done", "bool"),
    "lightCommandText": ("commands", "lines"), "alwaysCollate": ("collate_previous", "bool"),
    "subcontroller": ("subcontroller", "bool"), "customString": ("message", "str"), "fadeType": ("fade_type", "int"),
    "fadeNumberType": ("number_type", "int"), "fadeFrom": ("fade_from", "float"), "fadeTo": ("fade_to", "float"),
    "fps": ("fps", "int"), "pathWidth": ("path_width", "int"), "pathHeight": ("path_height", "int"),
    "messageType": ("message_type", "int"), "status": ("status", "int"), "channel": ("channel", "int"),
    "byte1": ("byte1", "int"), "byte2": ("byte2", "int"), "endValue": ("end_value", "int"),
    "commandFormat": ("command_format", "int"), "command": ("command", "int"), "deviceID": ("device_id", "int"),
    "qNumber": ("q_number", "str"), "qList": ("q_list", "str"), "qPath": ("q_path", "str"),
    "macro": ("macro", "int"), "controlNumber": ("control_number", "int"), "controlValue": ("control_value", "int"),
    "timecodeFormat": ("timecode_format", "int"), "rawString": ("raw_string", "str"),
    "devampType": ("devamp_type", "int"), "startNextCueWhenSliceEnds": ("start_next_when_slice_ends", "bool"),
    "stopTargetWhenSliceEnds": ("stop_target_when_slice_ends", "bool"), "scriptSource": ("script_source", "str"),
    "playlistLoop": ("playlist_loop", "bool"), "playlistShuffle": ("playlist_shuffle", "bool"),
    "playlistCrossfade": ("playlist_crossfade", "bool"),
    "playlistCrossfadeDuration": ("playlist_crossfade_duration", "float"), "cartRows": ("rows", "int"),
    "cartColumns": ("columns", "int"), "timecodeSyncMode": ("timecode_sync_mode", "int"),
    "timecodeSMPTEFormat": ("timecode_format", "int"), "timecodeStartBehavior": ("timecode_start_behavior", "int"),
    "timecodeStopBehavior": ("timecode_stop_behavior", "int"), "timecodeLookbackTime": ("timecode_lookback_time", "float"),
    "timecodeFreewheelTime": ("timecode_freewheel_time", "float"), "playbackRate": ("playback_rate", "float"),
    "audioTrackID": ("audio_track", "int"), "patch": ("audio_output_patch", "int"),
    "networkPatchNumber": ("network_patch", "int"), "midiPatchNumber": ("midi_patch", "int"),
    "cameraPatch": ("video_input_patch", "int"), "channels": ("channels", "int"), "channelOffset": ("first_input", "int"),
    "loadTime": ("load_time", "float"), "newTargetNumber": ("new_target_number", "str"),
    "playlistCrossfadeCurve": ("crossfade_curve_out", "json"), "videoEffects": ("video_fx", "json"),
}
LIST_PARAM_PROPS = {"translation": ("translation", 2), "scale": ("scale", 2), "anchor": ("anchor", 2),
                    "origin": ("origin", 2), "crop": ("crop", 4), "quaternion": ("quaternion", 4)}
SUBSCRIPTS = {"x": 0, "y": 1, "top": 0, "bottom": 1, "left": 2, "right": 3}
CROP_NAMES = {"cropTop": 0, "cropBottom": 1, "cropLeft": 2, "cropRight": 3}

ACTIONS = ["go", "start", "startAndAutoloadNext", "stop", "pause", "resume", "togglePause", "hardPause", "hardStop",
           "panic", "panicInTime", "preview", "auditionGo", "auditionPreview", "load", "loadAt", "loadActionAt",
           "loadFileAt", "loadAndSetPlayhead", "reset", "captureTimecode", "setDefaultLevels", "setSilentLevels",
           "resetRotation", "setGeometryFromTarget", "setLevelsFromTarget", "compileSource", "shuffle",
           "prune", "pruneCommands", "safeSort", "safeSortCommands", "collateAndStart"]


class Session:
    def __init__(self):
        self.permissions: dict = {}
        self.always_reply = False
        self.reply_format = ""
        self.updates = False
        self.forget_me_not = False
        self.last_seen = time.monotonic()
        self.client = None


class QLabApi:
    def __init__(self, runtimes: list[Runtime] | None = None, monotonic=time.monotonic, bonjour_name: str = ""):
        self.runtimes: list[Runtime] = []
        self.monotonic = monotonic
        self.sessions: dict[str, Session] = {}
        for runtime in runtimes or []:
            self.add_runtime(runtime)

    def add_runtime(self, runtime: Runtime) -> None:
        self.runtimes.append(runtime)
        runtime.listeners.append(lambda name, cue, data, rt=runtime: self._on_runtime_event(rt, name, cue, data))

    # ------------------------------------------------------------------ push
    def _on_runtime_event(self, runtime: Runtime, name: str, cue, data: dict) -> None:
        if name == "playhead":
            identifier = cue.unique_id if cue is not None else ""
            address = "/update/workspace/%s/cueList/%s/playbackPosition" % (runtime.workspace.workspace_id,
                                                                            data.get("list", ""))
            self._push(address, [identifier] if identifier != "" else [])

    def notify_workspace_changed(self, runtime: Runtime) -> None:
        self._push("/update/workspace/" + runtime.workspace.workspace_id, [])

    def notify_cue_changed(self, runtime: Runtime, cue: Cue) -> None:
        self._push("/update/workspace/%s/cue_id/%s" % (runtime.workspace.workspace_id, cue.unique_id), [])

    def _push(self, address: str, arguments: list) -> None:
        for session in list(self.sessions.values()):
            if session.updates == True and session.client is not None:
                session.client.send(address, arguments)

    # ------------------------------------------------------------------ sessione e permessi
    def _session_for(self, client) -> Session:
        now = self.monotonic()
        for key in [key for key, value in self.sessions.items() if value.forget_me_not == False
                    and value.client is not None and value.client.transport == "udp"
                    and now - value.last_seen > SESSION_TIMEOUT]:
            del self.sessions[key]
        key = client.identity()
        session = self.sessions.get(key)
        if session is None:
            session = Session()
            self.sessions[key] = session
        session.client = client
        session.last_seen = now
        return session

    def permissions_for(self, runtime: Runtime, session: Session) -> set:
        workspace_id = runtime.workspace.workspace_id
        if workspace_id in session.permissions:
            return session.permissions[workspace_id]
        for entry in runtime.workspace.settings.get("passcodes", []):
            if entry.get("passcode", "") == "":
                return self._entry_permissions(entry)
        return set()

    @staticmethod
    def _entry_permissions(entry: dict) -> set:
        permissions = set()
        if entry.get("view", False) == True:
            permissions.add("view")
            if entry.get("edit", False) == True:
                permissions.add("edit")
            if entry.get("control", False) == True:
                permissions.add("control")
        return permissions

    # ------------------------------------------------------------------ ingresso
    def handle(self, address: str, arguments: list, client) -> None:
        session = self._session_for(client)
        if address.startswith("/reply/"):
            return
        replies = self.process(address, arguments, session)
        for reply in replies:
            self._send_reply(client, session, reply)

    def _send_reply(self, client, session: Session, reply: dict) -> None:
        if reply["status"] == "ok" and reply.get("discrete", False) == True and session.always_reply == False:
            return
        payload = {"address": reply["address"], "status": reply["status"], "data": reply["data"]}
        if reply.get("workspace_id", "") != "":
            payload["workspace_id"] = reply["workspace_id"]
        if session.reply_format != "":
            text = session.reply_format
            text = text.replace("#workspace_id#", str(payload.get("workspace_id", "")))
            text = text.replace("#address#", payload["address"])
            text = text.replace("#status#", payload["status"])
            data = payload["data"]
            text = text.replace("#data#", data if isinstance(data, str) else json.dumps(data))
            client.send("/reply" + reply["sent_address"], [text])
        else:
            client.send("/reply" + reply["sent_address"], [json.dumps(payload)])

    def query(self, address: str, arguments: list | None = None, runtime: Runtime | None = None):
        """Valuta un indirizzo come lettura con tutti i permessi (OSC query dei Network cue)."""
        session = Session()
        session.always_reply = True
        target = runtime if runtime is not None else (self.runtimes[0] if len(self.runtimes) > 0 else None)
        if target is None:
            return None
        session.permissions[target.workspace.workspace_id] = {"view", "edit", "control"}
        replies = self.process(address, arguments or [], session, only=target)
        for reply in replies:
            if reply["status"] == "ok":
                return reply["data"]
        return None

    # ------------------------------------------------------------------ elaborazione
    def process(self, address: str, arguments: list, session: Session, only: Runtime | None = None) -> list[dict]:
        sent = address
        arguments = list(arguments)
        replies: list[dict] = []
        application = self._application_command(address, arguments, session)
        if application is not None:
            application["sent_address"] = sent
            application["address"] = address
            application.setdefault("workspace_id", "")
            return [application]
        targets = list(self.runtimes) if only is None else [only]
        stripped = address
        match = re.match(r"^/workspace/([^/]+)(/.*)?$", address)
        if match is not None:
            reference = match.group(1)
            stripped = match.group(2) or ""
            targets = [runtime for runtime in targets if self._workspace_matches(runtime, reference)]
            if len(targets) == 0:
                return [{"sent_address": sent, "address": stripped, "workspace_id": "", "status": "error",
                         "data": "workspace non trovato", "discrete": False}]
        any_handled = False
        for runtime in targets:
            result = self._run_for_workspace(runtime, stripped, arguments, session)
            result["sent_address"] = sent
            result["address"] = stripped
            result["workspace_id"] = runtime.workspace.workspace_id
            if result["status"] == "unhandled":
                continue
            any_handled = True
            replies.append(result)
        if any_handled == False and len(targets) > 0:
            replies.append({"sent_address": sent, "address": stripped, "workspace_id": "",
                            "status": "error", "data": "indirizzo sconosciuto", "discrete": False})
        return replies

    @staticmethod
    def _workspace_matches(runtime: Runtime, reference: str) -> bool:
        workspace = runtime.workspace
        if reference == workspace.workspace_id:
            return True
        cleaned = re.sub(r"[^A-Za-z0-9_\-]", "", workspace.name.rsplit(".", 1)[0])
        return reference == cleaned or reference == workspace.name

    def _application_command(self, address: str, arguments: list, session: Session):
        if address == "/version":
            return {"status": "ok", "data": API_VERSION, "discrete": False}
        if address == "/workspaces":
            data = [{"uniqueID": runtime.workspace.workspace_id, "displayName": runtime.workspace.name,
                     "port": runtime.workspace.settings.get("osc_port", 53000),
                     "udpReplyPort": runtime.workspace.settings.get("osc_reply_port", 53001),
                     "version": API_VERSION} for runtime in self.runtimes]
            return {"status": "ok", "data": data, "discrete": False}
        if address == "/disconnect":
            session.permissions.clear()
            return {"status": "ok", "data": "ok", "discrete": True}
        if address == "/alwaysReply":
            if len(arguments) > 0:
                session.always_reply = to_bool(arguments[0])
            return {"status": "ok", "data": session.always_reply, "discrete": len(arguments) > 0}
        if address == "/replyFormat":
            if len(arguments) > 0:
                session.reply_format = str(arguments[0])
            return {"status": "ok", "data": session.reply_format, "discrete": len(arguments) > 0}
        if address in ("/forgetMeNot", "/udpKeepAlive"):
            if len(arguments) > 0:
                session.forget_me_not = to_bool(arguments[0])
            return {"status": "ok", "data": session.forget_me_not, "discrete": len(arguments) > 0}
        if address == "/updates":
            if len(arguments) > 0:
                session.updates = to_bool(arguments[0])
            return {"status": "ok", "data": session.updates, "discrete": len(arguments) > 0}
        if address == "/thump":
            return {"status": "ok", "data": "thump", "discrete": False}
        if address.startswith("/overrides/"):
            return self._overrides(address[len("/overrides/"):], arguments)
        return None

    def _overrides(self, tail: str, arguments: list) -> dict:
        names = ["dmxOutput", "midiInput", "midiOutput", "mscInput", "mscOutput", "sysexInput", "sysexOutput",
                 "networkExternalInput", "networkExternalOutput", "networkLocalInput", "networkLocalOutput",
                 "timecodeInput", "timecodeOutput"]
        toggle = False
        key = tail
        if tail.startswith("toggle"):
            toggle = True
            key = tail[6].lower() + tail[7:]
        elif tail.endswith("Enabled"):
            key = tail[:-7]
        if key not in names:
            return {"status": "error", "data": "override sconosciuto", "discrete": False}
        for runtime in self.runtimes:
            overrides = runtime.workspace.settings["overrides"]
            if toggle == True:
                overrides[key] = overrides.get(key, True) == False
            elif len(arguments) > 0:
                overrides[key] = to_bool(arguments[0])
            value = overrides.get(key, True)
        return {"status": "ok", "data": value if len(self.runtimes) > 0 else True,
                "discrete": toggle or len(arguments) > 0}

    # ------------------------------------------------------------------ workspace
    def _run_for_workspace(self, runtime: Runtime, path: str, arguments: list, session: Session) -> dict:
        permissions = self.permissions_for(runtime, session)
        parts = [part for part in path.split("/") if part != ""]
        if len(parts) == 0:
            return {"status": "unhandled", "data": None}
        with runtime.lock:
            try:
                if parts[0] == "connect":
                    return self._connect(runtime, session, arguments)
                if parts[0] == "updates":
                    return {"status": "ok", "data": self._set_updates(session, arguments), "discrete": True}
                return self._dispatch(runtime, parts, arguments, permissions)
            except ApiError as problem:
                return {"status": problem.status, "data": str(problem), "discrete": False}
            except (ValueError, KeyError, IndexError, TypeError) as problem:
                return {"status": "error", "data": "%s: %s" % (type(problem).__name__, problem), "discrete": False}

    @staticmethod
    def _set_updates(session: Session, arguments: list) -> bool:
        if len(arguments) > 0:
            session.updates = to_bool(arguments[0])
        return session.updates

    def _connect(self, runtime: Runtime, session: Session, arguments: list) -> dict:
        passcode = str(arguments[0]) if len(arguments) > 0 else ""
        for entry in runtime.workspace.settings.get("passcodes", []):
            if str(entry.get("passcode", "")) == passcode:
                session.permissions[runtime.workspace.workspace_id] = self._entry_permissions(entry)
                return {"status": "ok", "data": "ok", "discrete": False}
        return {"status": "error", "data": "badpass", "discrete": False}

    @staticmethod
    def _need(permissions: set, wanted: str) -> None:
        if wanted not in permissions:
            raise ApiError("permesso negato", "denied")

    def _dispatch(self, runtime: Runtime, parts: list, arguments: list, permissions: set) -> dict:
        head = parts[0]
        if head == "cue" and len(parts) >= 2:
            cues = self._resolve_cues(runtime, parts[1])
            return self._cue_command(runtime, cues, parts[2:], arguments, permissions, plural=has_wildcard(parts[1])
                                     or parts[1] in ("selected", "active"))
        if head == "cue_id" and len(parts) >= 2:
            cue = runtime.workspace.find_by_id(parts[1])
            if cue is None:
                raise ApiError("cue non trovato")
            return self._cue_command(runtime, [cue], parts[2:], arguments, permissions, plural=False)
        return self._workspace_command(runtime, parts, arguments, permissions)

    # ------------------------------------------------------------------ risoluzione cue
    def _resolve_cues(self, runtime: Runtime, reference: str) -> list[Cue]:
        workspace = runtime.workspace
        if reference == "selected":
            return [found for found in (workspace.find_by_id(identifier) for identifier in runtime.selection)
                    if found is not None]
        if reference in ("playhead", "playbackPosition"):
            found = runtime.playhead()
            return [found] if found is not None else []
        if reference == "active":
            return runtime.active_cues()
        if has_wildcard(reference) == True:
            result = []
            for cue in workspace.all_cues():
                if reference == "[*]":
                    if cue.number != "":
                        result.append(cue)
                elif cue.number != "" and pattern_matches(reference, cue.number):
                    result.append(cue)
            return result
        found = workspace.find_by_number(reference)
        if found is None:
            for container in workspace.lists:
                if container.number == reference:
                    found = container
        if found is None:
            raise ApiError("cue non trovato: " + reference)
        return [found]

    # ------------------------------------------------------------------ info cue
    def cue_info(self, runtime: Runtime, cue: Cue, shallow: bool = False) -> dict:
        workspace = runtime.workspace
        root = cue.root_list()
        info = {"uniqueID": cue.unique_id, "number": cue.number, "name": cue.display_name(workspace),
                "listName": cue.list_name(workspace), "type": TYPE_NAMES.get(cue.cue_type, cue.cue_type),
                "colorName": runtime.current_color(cue), "colorName/live": runtime.current_color(cue),
                "flagged": cue.flagged, "armed": cue.armed}
        if cue.is_group_like() == True and shallow == False:
            info["cues"] = [self.cue_info(runtime, child) for child in cue.children]
        return info

    # ------------------------------------------------------------------ comandi cue
    def _cue_command(self, runtime: Runtime, cues: list[Cue], parts: list, arguments: list, permissions: set,
                     plural: bool) -> dict:
        if len(parts) == 0:
            raise ApiError("manca la proprietà")
        increment = 0
        live = False
        working = list(parts)
        if working[-1] in ("+", "-") and len(working) > 1:
            increment = 1 if working[-1] == "+" else -1
            working = working[:-1]
        if working[-1] == "live" and len(working) > 1:
            live = True
            working = working[:-1]
        name = working[0]
        subpath = working[1:]
        if name in ACTIONS:
            self._need(permissions, "control")
            for cue in cues:
                self._action(runtime, cue, name, arguments, subpath)
            return {"status": "ok", "data": "ok", "discrete": True}
        if len(arguments) == 0 and increment == 0:
            self._need(permissions, "view")
            values = [self._get(runtime, cue, name, subpath) for cue in cues]
            return {"status": "ok", "data": values if plural == True else values[0], "discrete": False}
        self._need(permissions, "edit")
        for cue in cues:
            self._set(runtime, cue, name, subpath, arguments, increment, live)
        runtime.workspace.modified = runtime.workspace.modified or live == False
        for cue in cues:
            self.notify_cue_changed(runtime, cue)
        return {"status": "ok", "data": "ok", "discrete": True}

    def _action(self, runtime: Runtime, cue: Cue, name: str, arguments: list, subpath: list) -> None:
        if name in ("go", "start"):
            runtime.start_cue(cue, origin=ORIGIN_OSC)
        elif name == "startAndAutoloadNext":
            runtime.start_cue(cue, origin=ORIGIN_OSC)
            following = runtime.next_sibling(cue)
            runtime.load_cue(following)
        elif name == "stop":
            runtime.stop_cue(cue)
        elif name == "pause":
            runtime.pause_cue(cue)
        elif name == "hardPause":
            runtime.pause_cue(cue)
        elif name == "resume":
            runtime.resume_cue(cue)
        elif name == "togglePause":
            state = runtime.states.get(cue.unique_id)
            if state is not None and state.paused == True:
                runtime.resume_cue(cue)
            else:
                runtime.pause_cue(cue)
        elif name == "hardStop":
            runtime.stop_cue(cue, hard=True)
        elif name == "panic":
            runtime.panic_cue(cue)
        elif name == "panicInTime":
            runtime.panic_cue(cue)
        elif name in ("preview", "auditionPreview"):
            runtime.start_cue(cue, origin=ORIGIN_OSC, preview=True, audition=name == "auditionPreview")
        elif name == "auditionGo":
            runtime.start_cue(cue, origin=ORIGIN_OSC, audition=True)
        elif name == "load":
            runtime.load_cue(cue)
        elif name in ("loadAt", "loadActionAt", "loadFileAt"):
            runtime.load_cue(cue, to_float(arguments[0]) if len(arguments) > 0 else 0.0)
        elif name == "loadAndSetPlayhead":
            runtime.load_cue(cue)
            runtime.set_playhead(cue)
        elif name == "reset":
            runtime.reset_cue(cue)
        elif name == "compileSource":
            runtime.compile_script(cue)
        elif name == "setSilentLevels":
            cue.params["levels"] = {}
        elif name == "setDefaultLevels":
            cue.params["levels"] = {"main": 0.0}
        elif name == "resetRotation":
            cue.params["quaternion"] = [1.0, 0.0, 0.0, 0.0]
        elif name == "shuffle":
            runtime.random.shuffle(cue.children)
        elif name in ("safeSort", "safeSortCommands"):
            cue.params["commands"] = sorted(cue.params.get("commands", []))
        elif name in ("prune", "pruneCommands"):
            cue.params["commands"] = list(dict.fromkeys(cue.params.get("commands", [])))
        elif name == "setLevelsFromTarget":
            target = runtime.resolve_target(cue)
            if target is not None:
                cue.params["levels"] = dict(target.params.get("levels", {}))
        elif name == "setGeometryFromTarget":
            target = runtime.resolve_target(cue)
            if target is not None:
                for key in ("opacity", "translation", "scale", "quaternion"):
                    if key in target.params:
                        cue.params[key] = target.params[key]
        elif name == "collateAndStart":
            cue.params["collate_previous"] = True
            runtime.start_cue(cue, origin=ORIGIN_OSC)

    # --- letture ---
    def _get(self, runtime: Runtime, cue: Cue, name: str, subpath: list):
        workspace = runtime.workspace
        status = runtime.status(cue)
        state = runtime.states.get(cue.unique_id)
        if name == "uniqueID":
            return cue.unique_id
        if name == "number":
            return cue.number
        if name == "name":
            return cue.name if cue.name != "" else cue.default_name(workspace)
        if name in ("displayName",):
            return cue.display_name(workspace)
        if name == "listName":
            return cue.list_name(workspace)
        if name == "defaultName":
            return cue.default_name(workspace)
        if name == "type":
            return TYPE_NAMES.get(cue.cue_type, cue.cue_type)
        if name == "notes":
            return cue.notes
        if name == "parent":
            return cue.parent.unique_id if cue.parent is not None else ""
        if name == "armed":
            return cue.armed
        if name == "autoLoad":
            return cue.auto_load
        if name == "flagged":
            return cue.flagged
        if name == "colorName":
            return runtime.current_color(cue) if subpath == ["live"] else cue.color
        if name == "colorCondition":
            return COLOR_CONDITIONS.index(cue.color_condition)
        if name == "continueMode":
            return cue.continue_mode
        if name == "preWait":
            return cue.pre_wait
        if name == "postWait":
            return cue.post_wait
        if name == "duration":
            return cue.duration
        if name == "currentDuration":
            value = status["action_duration"]
            return cue.duration if value == INFINITE else value
        if name == "cueTargetID":
            target = workspace.find_target(cue)
            return target.unique_id if target is not None else ""
        if name == "cueTargetNumber":
            target = workspace.find_target(cue)
            return target.number if target is not None else ""
        if name == "currentCueTarget":
            target = runtime.resolve_target(cue)
            return target.unique_id if target is not None else ""
        if name == "tempCueTargetID":
            return runtime.temp_targets.get(cue.unique_id, "")
        if name == "tempCueTargetNumber":
            target = workspace.find_by_id(runtime.temp_targets.get(cue.unique_id, ""))
            return target.number if target is not None else ""
        if name == "fileTarget":
            return cue.params.get("file_target", "")
        if name == "secondTriggerAction":
            return cue.second_trigger_action
        if name == "secondTriggerOnRelease":
            return cue.second_trigger_on_release
        if name == "duckOthers":
            return cue.duck_others.get("enabled", False)
        if name == "duckLevel":
            return cue.duck_others.get("level", -12.0)
        if name == "duckTime":
            return cue.duck_others.get("time", 1.0)
        if name == "fadeAndStopOthers":
            return cue.fade_and_stop_others.get("mode", 0)
        if name == "fadeAndStopOthersTime":
            return cue.fade_and_stop_others.get("time", 0.0)
        flags = {"isLoaded": "loaded", "isRunning": "running", "isPaused": "paused", "isBroken": "broken",
                 "isActionRunning": "running", "isCrossfadingOut": "crossfading_out", "isPanicking": "panicking",
                 "isTailingOut": "tailing_out"}
        if name in flags:
            if name == "isRunning":
                return state is not None and state.is_active()
            return status[flags[name]]
        if name in ("isWarning", "isAuditioning", "isOverridden"):
            return state.audition if (state is not None and name == "isAuditioning") else False
        if name == "isChildFlagged":
            return any(child.flagged for child in cue.walk() if child is not cue)
        if name == "actionElapsed":
            return status["action_elapsed"]
        if name == "preWaitElapsed":
            return status["pre_wait_elapsed"]
        if name == "postWaitElapsed":
            return status["post_wait_elapsed"]
        if name in ("percentActionElapsed", "percentPreWaitElapsed", "percentPostWaitElapsed"):
            return self._percent(runtime, cue, name, status)
        if name == "maxTimeInCueSequence":
            return sum(item.pre_wait + max(item.duration, item.post_wait) for item in runtime.sequence_cues(cue))
        if name == "allowsEditingDuration":
            return cue.allows_editing_duration()
        if name == "hasCueTargets":
            return cue.has_cue_target()
        if name == "hasFileTargets":
            return cue.has_file_target()
        if name == "cartPosition":
            position = [cue.cart_row, cue.cart_column] if (cue.parent is not None and cue.parent.cue_type == TYPE_CART) else [0, 0]
            if subpath == ["row"]:
                return position[0]
            if subpath == ["column"]:
                return position[1]
            return position
        if name == "children":
            shallow = "shallow" in subpath
            if "uniqueIDs" in subpath:
                return [child.unique_id for child in cue.children]
            return [self.cue_info(runtime, child, shallow=shallow) for child in cue.children]
        if name == "mode":
            return cue.group_mode()
        if name in ("playhead", "playbackPosition"):
            found = runtime.playhead(cue)
            return found.number if found is not None else ""
        if name in ("playheadID", "playbackPositionID"):
            found = runtime.playhead(cue)
            return found.unique_id if found is not None else ""
        if name == "doFade":
            return cue.params.get("integrated_fade", {}).get("enabled", False)
        if name == "sliceMarkers":
            return cue.params.get("slices", [])
        if name == "levels":
            return cue.params.get("levels", {})
        if name == "level":
            return self._get_level(runtime, cue, subpath)
        if name == "valuesForKeys":
            return self._values_for_keys(runtime, cue)
        if name == "levelsMode":
            return GEO_MODES.index(cue.params.get("levels_mode", "absolute"))
        if name in ("geoMode", "mode") and cue.cue_type == "fade":
            return GEO_MODES.index(cue.params.get("geometry_mode", "absolute"))
        if name == "geoMode":
            return GEO_MODES.index(cue.params.get("geometry_mode", "absolute"))
        if name == "currentFileTime":
            if state is not None and state.plan is not None:
                position = state.plan.locate(state.action_elapsed)
                return position["media_time"] if position is not None else 0.0
            return 0.0
        if name in ("cueSize",):
            return cue.params.get("cue_size", [0, 0])
        if name in LIST_PARAM_PROPS or name in CROP_NAMES:
            return self._get_list_prop(runtime, cue, name, subpath)
        if name == "text" and subpath == []:
            return cue.params.get("text", "")
        if name in PARAM_PROPS:
            key, kind = PARAM_PROPS[name]
            value = runtime.get_param(cue, key)
            if kind == "lines":
                return "\n".join(value or [])
            return value
        if name == "currentTimecode" or name == "timecodeTrigger":
            return cue.triggers.get("timecode") or ""
        raise ApiError("proprietà sconosciuta: " + name)

    @staticmethod
    def _percent(runtime: Runtime, cue: Cue, name: str, status: dict) -> float:
        if name == "percentPreWaitElapsed":
            total = cue.pre_wait
            elapsed = status["pre_wait_elapsed"]
        elif name == "percentPostWaitElapsed":
            total = cue.post_wait
            elapsed = status["post_wait_elapsed"]
        else:
            total = status["action_duration"]
            elapsed = status["action_elapsed"]
        if total <= 0 or total == INFINITE:
            return 0.0
        return min(1.0, elapsed / total)

    def _values_for_keys(self, runtime: Runtime, cue: Cue):
        return {}

    def _get_level(self, runtime: Runtime, cue: Cue, subpath: list):
        levels = runtime.get_param(cue, "levels", {})
        key = self._level_key(subpath)
        return levels.get(key, 0.0 if key == "main" else float(runtime.workspace.settings["min_volume"]))

    @staticmethod
    def _level_key(subpath: list, arguments: list | None = None) -> str:
        indexes = list(subpath)
        if arguments is not None and len(indexes) == 0:
            indexes = [str(arguments[0]), str(arguments[1])]
        if len(indexes) < 2:
            raise ApiError("servono input e output")
        if int(float(indexes[0])) == 0 and int(float(indexes[1])) == 0:
            return "main"
        return "%d/%d" % (int(float(indexes[0])), int(float(indexes[1])))

    def _get_list_prop(self, runtime: Runtime, cue: Cue, name: str, subpath: list):
        if name in CROP_NAMES:
            return runtime.get_param(cue, "crop", [0, 0, 0, 0])[CROP_NAMES[name]]
        key, size = LIST_PARAM_PROPS[name]
        default = [1.0, 0.0, 0.0, 0.0] if name == "quaternion" else ([1.0, 1.0] if name == "scale" else [0.0] * size)
        value = list(runtime.get_param(cue, key, default))
        if len(subpath) == 1 and subpath[0] in SUBSCRIPTS:
            return value[SUBSCRIPTS[subpath[0]]]
        return value

    # --- scritture ---
    def _set(self, runtime: Runtime, cue: Cue, name: str, subpath: list, arguments: list, increment: int,
             live: bool) -> None:
        workspace = runtime.workspace
        first = arguments[0] if len(arguments) > 0 else None
        if name == "number":
            try:
                workspace.set_number(cue, str(first))
            except (DuplicateNumberError, InvalidNumberError) as problem:
                raise ApiError(str(problem))
            return
        if name == "name":
            cue.name = str(first)
            return
        if name == "notes":
            cue.notes = str(first)
            return
        if name == "armed":
            cue.armed = to_bool(first)
            return
        if name == "autoLoad":
            cue.auto_load = to_bool(first)
            return
        if name == "flagged":
            cue.flagged = to_bool(first)
            return
        if name == "colorName":
            color = str(first).lower()
            if color not in COLORS:
                raise ApiError("colore sconosciuto")
            cue.color = color
            return
        if name == "colorCondition":
            cue.color_condition = COLOR_CONDITIONS[to_int(first)]
            return
        if name == "continueMode":
            cue.continue_mode = max(0, min(2, to_int(first)))
            return
        if name in ("preWait", "postWait", "duration"):
            attribute = {"preWait": "pre_wait", "postWait": "post_wait", "duration": "duration"}[name]
            if name == "duration" and cue.allows_editing_duration() == False:
                raise ApiError("durata non modificabile per questo tipo")
            value = to_float(first)
            if increment != 0:
                value = getattr(cue, attribute) + increment * value
            setattr(cue, attribute, max(0.0, value))
            return
        if name in ("cueTargetID", "cueTargetNumber"):
            if str(first) in ("", "none"):
                cue.target_id = ""
                cue.target_number = ""
                return
            found = workspace.find_by_id(str(first)) if name == "cueTargetID" else workspace.find_by_number(str(first))
            if found is None:
                raise ApiError("target non trovato")
            cue.target_id = found.unique_id
            cue.target_number = ""
            return
        if name in ("tempCueTargetID", "tempCueTargetNumber"):
            found = workspace.find_by_id(str(first)) if name == "tempCueTargetID" else workspace.find_by_number(str(first))
            if found is None:
                runtime.temp_targets.pop(cue.unique_id, None)
            else:
                runtime.temp_targets[cue.unique_id] = found.unique_id
            return
        if name == "fileTarget":
            cue.params["file_target"] = str(first)
            return
        if name == "secondTriggerAction":
            cue.second_trigger_action = to_int(first)
            return
        if name == "secondTriggerOnRelease":
            cue.second_trigger_on_release = to_bool(first)
            return
        if name == "duckOthers":
            cue.duck_others["enabled"] = to_bool(first)
            return
        if name in ("duckLevel", "duckTime"):
            cue.duck_others["level" if name == "duckLevel" else "time"] = to_float(first)
            return
        if name == "fadeAndStopOthers":
            cue.fade_and_stop_others["mode"] = to_int(first)
            return
        if name == "fadeAndStopOthersTime":
            cue.fade_and_stop_others["time"] = to_float(first)
            return
        if name == "doFade":
            cue.params["integrated_fade"]["enabled"] = to_bool(first)
            return
        if name in ("playhead", "playbackPosition", "playheadID", "playbackPositionID"):
            found = workspace.find_by_number(str(first)) if name in ("playhead", "playbackPosition") \
                else workspace.find_by_id(str(first))
            runtime.set_playhead(found, cue)
            return
        if name == "level":
            key = self._level_key(subpath, arguments)
            value = to_float(arguments[-1])
            levels = dict(cue.params.get("levels", {}))
            levels[key] = value
            if live == True:
                runtime.set_live_param(cue, "levels", levels)
            else:
                cue.params["levels"] = levels
            return
        if name == "addSliceMarker":
            count = to_int(arguments[1]) if len(arguments) > 1 else 1
            cue.params["slices"].append({"time": to_float(first), "play_count": "inf" if count < 0 else count})
            return
        if name == "deleteSliceMarker":
            del cue.params["slices"][to_int(first)]
            return
        if name == "deleteSliceMarkers":
            cue.params["slices"] = []
            return
        if name == "sliceMarker":
            index = to_int(first)
            cue.params["slices"][index] = {"time": to_float(arguments[1]),
                                           "play_count": "inf" if to_int(arguments[2]) < 0 else to_int(arguments[2])}
            return
        if name in ("levelsMode", "geoMode", "mode") and cue.cue_type == "fade":
            attribute = "geometry_mode" if name == "geoMode" else "levels_mode"
            cue.params[attribute] = GEO_MODES[to_int(first)]
            return
        if name in ("willFade",):
            key = "%d/%d" % (to_int(arguments[0]), to_int(arguments[1]))
            levels = cue.params.setdefault("levels", {})
            if to_bool(arguments[2]) == True:
                levels.setdefault(key, 0.0)
            else:
                levels.pop(key, None)
            return
        if name == "mode" and cue.cue_type == TYPE_GROUP:
            cue.params["group_mode"] = to_int(first)
            return
        if name in LIST_PARAM_PROPS or name in CROP_NAMES:
            self._set_list_prop(runtime, cue, name, subpath, arguments, live)
            return
        if name in PARAM_PROPS:
            key, kind = PARAM_PROPS[name]
            if kind == "lines":
                value = [line for line in str(first).split("\n") if line != ""]
            else:
                value = CONVERTERS[kind](first)
                if increment != 0 and kind in ("float", "int"):
                    value = runtime.get_param(cue, key, 0) + increment * value
            if live == True:
                runtime.set_live_param(cue, key, value)
            else:
                cue.params[key] = value
            return
        raise ApiError("proprietà non scrivibile: " + name)

    def _set_list_prop(self, runtime: Runtime, cue: Cue, name: str, subpath: list, arguments: list,
                       live: bool) -> None:
        if name in CROP_NAMES:
            key, size = "crop", 4
            value = list(runtime.get_param(cue, key, [0, 0, 0, 0]))
            value[CROP_NAMES[name]] = to_float(arguments[0])
        else:
            key, size = LIST_PARAM_PROPS[name]
            default = [1.0, 0.0, 0.0, 0.0] if name == "quaternion" else ([1.0, 1.0] if name == "scale" else [0.0] * size)
            value = list(runtime.get_param(cue, key, default))
            if len(subpath) == 1 and subpath[0] in SUBSCRIPTS:
                value[SUBSCRIPTS[subpath[0]]] = to_float(arguments[0])
            else:
                if len(arguments) == 1 and isinstance(arguments[0], str):
                    arguments = [to_float(token) for token in re.split(r"[ ,]+", arguments[0].strip("[] "))]
                if len(arguments) < size:
                    raise ApiError("servono %d valori" % size)
                value = [to_float(item) for item in arguments[:size]]
        if live == True:
            runtime.set_live_param(cue, key, value)
        else:
            cue.params[key] = value

    # ------------------------------------------------------------------ comandi workspace
    def _workspace_command(self, runtime: Runtime, parts: list, arguments: list, permissions: set) -> dict:
        workspace = runtime.workspace
        head = parts[0]
        tail = parts[1:]
        control = {"go", "auditionGo", "pause", "resume", "stop", "hardStop", "panic", "panicInTime", "reset",
                   "playhead", "playheadID", "playbackPosition", "playbackPositionID"}
        if head in control:
            self._need(permissions, "control")
            self._control(runtime, head, tail, arguments)
            return {"status": "ok", "data": "ok", "discrete": True}
        if head == "select" or head == "select_id":
            self._need(permissions, "view")
            self._select(runtime, head, tail)
            return {"status": "ok", "data": "ok", "discrete": True}
        if head in ("new", "delete", "delete_id", "move", "renumber", "undo", "redo", "save"):
            self._need(permissions, "edit")
            return self._edit(runtime, head, tail, arguments)
        self._need(permissions, "view")
        lists = {"cueLists": lambda: [self.cue_info(runtime, container) for container in workspace.lists],
                 "selectedCues": lambda: [self.cue_info(runtime, cue) for cue in self._resolve_cues(runtime, "selected")],
                 "runningCues": lambda: [self.cue_info(runtime, state.cue) for state in runtime.states.values()
                                         if state.action_running],
                 "runningOrPausedCues": lambda: [self.cue_info(runtime, cue) for cue in runtime.active_cues()]}
        if head in lists:
            value = lists[head]()
            if "shallow" in tail:
                value = [self._strip_children(item) for item in value]
            if "uniqueIDs" in tail:
                value = [item["uniqueID"] for item in value]
            return {"status": "ok", "data": value, "discrete": False}
        if head == "basePath":
            import os
            return {"status": "ok", "data": os.path.dirname(workspace.path) if workspace.path else "",
                    "discrete": False}
        if head == "thump":
            return {"status": "ok", "data": "thump", "discrete": False}
        if head == "doubleGoWindowRemaining":
            minimum = float(workspace.settings.get("min_go_time", 0.0))
            remaining = max(0.0, minimum - (runtime.clock.now() - runtime._last_go_time))
            return {"status": "ok", "data": remaining, "discrete": False}
        if head in ("currentCueList", "currentCueListID"):
            if len(arguments) > 0:
                self._need(permissions, "edit")
                found = workspace.find_list(str(arguments[0]))
                if found is None:
                    raise ApiError("lista non trovata")
                workspace.active_list_id = found.unique_id
                return {"status": "ok", "data": "ok", "discrete": True}
            active = workspace.active_list()
            return {"status": "ok", "data": active.unique_id if head.endswith("ID") else active.display_name(),
                    "discrete": False}
        if head == "showMode" or head == "toggleEditShowMode":
            if head == "toggleEditShowMode":
                workspace.settings["show_mode"] = workspace.settings.get("show_mode", False) == False
            elif len(arguments) > 0:
                workspace.settings["show_mode"] = to_bool(arguments[0])
            return {"status": "ok", "data": workspace.settings.get("show_mode", False),
                    "discrete": len(arguments) > 0 or head == "toggleEditShowMode"}
        if head == "alwaysAudition":
            if len(arguments) > 0:
                workspace.settings["always_audition"] = to_bool(arguments[0])
            return {"status": "ok", "data": workspace.settings.get("always_audition", False),
                    "discrete": len(arguments) > 0}
        if head == "settings":
            return self._settings(runtime, tail, arguments, permissions)
        if head == "dashboard":
            self._need(permissions, "edit")
            bridge = runtime.light_bridge
            if bridge is None or hasattr(bridge, "dashboard") == False:
                raise ApiError("sezione Light non collegata")
            return {"status": "ok", "data": bridge.dashboard(tail, arguments), "discrete": True}
        raise_unhandled = {"status": "unhandled", "data": None}
        return raise_unhandled

    @staticmethod
    def _strip_children(item: dict) -> dict:
        copy_item = dict(item)
        copy_item.pop("cues", None)
        return copy_item

    def _control(self, runtime: Runtime, head: str, tail: list, arguments: list) -> None:
        workspace = runtime.workspace
        if head in ("go", "auditionGo"):
            reference = tail[0] if len(tail) > 0 else (str(arguments[0]) if len(arguments) > 0 else "")
            audition = head == "auditionGo"
            if reference != "":
                cue = workspace.find_by_number(reference)
                if cue is None:
                    raise ApiError("cue non trovato")
                runtime.start_cue(cue, origin=ORIGIN_OSC, audition=audition)
            else:
                runtime.go(origin=ORIGIN_OSC, audition=audition)
        elif head == "pause":
            runtime.pause_all()
        elif head == "resume":
            runtime.resume_all()
        elif head == "stop":
            for state in list(runtime.states.values()):
                runtime.stop_cue(state.cue)
        elif head == "hardStop":
            runtime.hard_stop_all()
        elif head in ("panic", "panicInTime"):
            if head == "panicInTime" and len(arguments) > 0:
                workspace.settings["panic_duration"] = max(0.0, to_float(arguments[0]))
            runtime.panic_all()
        elif head == "reset":
            runtime.reset_workspace()
        else:
            self._playhead(runtime, head, tail, arguments)

    def _playhead(self, runtime: Runtime, head: str, tail: list, arguments: list) -> None:
        workspace = runtime.workspace
        reference = tail[0] if len(tail) > 0 else (str(arguments[0]) if len(arguments) > 0 else "")
        if reference == "next":
            runtime.move_playhead_next()
        elif reference == "previous":
            runtime.move_playhead_previous()
        elif reference == "nextSequence":
            runtime.move_playhead_next_sequence()
        elif reference == "previousSequence":
            runtime.move_playhead_previous_sequence()
        elif reference == "selected":
            selected = self._resolve_cues(runtime, "selected")
            if len(selected) > 0:
                runtime.set_playhead(selected[0])
        elif reference == "active":
            active = runtime.active_cues()
            if len(active) > 0:
                runtime.set_playhead(active[0])
        elif reference == "none" or reference == "":
            runtime.set_playhead(None)
        else:
            found = workspace.find_by_id(reference) if head.endswith("ID") else workspace.find_by_number(reference)
            if found is None:
                raise ApiError("cue non trovato")
            runtime.set_playhead(found)

    def _select(self, runtime: Runtime, head: str, tail: list) -> None:
        workspace = runtime.workspace
        reference = tail[0] if len(tail) > 0 else ""
        if reference in ("next", "previous"):
            current = [workspace.find_by_id(identifier) for identifier in runtime.selection]
            base = current[-1] if len(current) > 0 and current[-1] is not None else runtime.playhead()
            if base is None:
                return
            found = runtime.next_after(base) if reference == "next" else runtime.previous_sibling(base)
            if found is not None:
                runtime.set_selection([found])
            return
        found = workspace.find_by_id(reference) if head == "select_id" else workspace.find_by_number(reference)
        if found is None:
            raise ApiError("cue non trovato")
        runtime.set_selection([found])

    def _edit(self, runtime: Runtime, head: str, tail: list, arguments: list) -> dict:
        workspace = runtime.workspace
        if head == "new":
            kind = str(arguments[0]).lower() if len(arguments) > 0 else (tail[0] if tail else "")
            kind = NEW_TYPE_ALIASES.get(kind, kind)
            if kind in (TYPE_LIST, TYPE_CART):
                container = workspace.new_list("", cart=kind == TYPE_CART)
                runtime.ensure_playheads()
                return {"status": "ok", "data": container.unique_id, "discrete": False}
            if kind not in CUE_TYPES:
                raise ApiError("tipo di cue sconosciuto: " + kind)
            parent = workspace.active_list()
            index = None
            anchor = None
            if len(arguments) > 1:
                anchor = workspace.find_by_id(str(arguments[1]))
            elif len(runtime.selection) > 0:
                anchor = workspace.find_by_id(runtime.selection[-1])
            if anchor is not None:
                if anchor.is_container() == True:
                    parent = anchor
                else:
                    parent = anchor.parent
                    index = parent.children.index(anchor) + 1
            cue = workspace.new_cue(kind, parent=parent, index=index, auto_number=False)
            if parent.cue_type == TYPE_CART and len(arguments) >= 4:
                cue.cart_row = to_int(arguments[2])
                cue.cart_column = to_int(arguments[3])
            runtime.ensure_playheads()
            runtime.set_selection([cue])
            self.notify_workspace_changed(runtime)
            return {"status": "ok", "data": cue.unique_id, "discrete": False}
        if head in ("delete", "delete_id"):
            reference = tail[0] if tail else ""
            if reference == "selected":
                victims = self._resolve_cues(runtime, "selected")
            elif reference == "active":
                victims = runtime.active_cues()
            elif head == "delete_id":
                victims = [workspace.find_by_id(reference)]
            else:
                victims = [workspace.find_by_number(reference)]
            for cue in victims:
                if cue is None or cue.parent is None:
                    raise ApiError("cue non trovato")
                runtime.stop_cue(cue, hard=True)
                workspace.delete_cue(cue)
            runtime.ensure_playheads()
            self.notify_workspace_changed(runtime)
            return {"status": "ok", "data": "ok", "discrete": True}
        if head == "move":
            cue = workspace.find_by_id(str(arguments[0]))
            index = to_int(arguments[1])
            parent = workspace.find_by_id(str(arguments[2])) if len(arguments) > 2 else cue.parent
            workspace.move_cue(cue, parent, index)
            self.notify_workspace_changed(runtime)
            return {"status": "ok", "data": "ok", "discrete": True}
        if head == "renumber":
            selected = self._resolve_cues(runtime, "selected")
            start = to_float(arguments[0])
            increment = to_float(arguments[1]) if len(arguments) > 1 else 1.0
            prefix = str(arguments[2]) if len(arguments) > 2 else ""
            suffix = str(arguments[3]) if len(arguments) > 3 else ""
            workspace.renumber(selected, start, increment, prefix, suffix)
            return {"status": "ok", "data": "ok", "discrete": True}
        if head == "undo":
            workspace.undo()
            runtime.ensure_playheads()
            return {"status": "ok", "data": "ok", "discrete": True}
        if head == "redo":
            workspace.redo()
            runtime.ensure_playheads()
            return {"status": "ok", "data": "ok", "discrete": True}
        if head == "save":
            workspace.save()
            return {"status": "ok", "data": "ok", "discrete": True}
        raise ApiError("comando sconosciuto")

    def _settings(self, runtime: Runtime, tail: list, arguments: list, permissions: set) -> dict:
        settings = runtime.workspace.settings
        key = "/".join(tail)
        simple = {"general/minGoTime": ("min_go_time", "float"),
                  "general/selectionIsPlayhead": ("lock_playhead_to_selection", "bool"),
                  "audio/maxVolume": ("max_volume", "float"), "audio/minVolume": ("min_volume", "float")}
        if key in simple:
            name, kind = simple[key]
            if len(arguments) > 0:
                self._need(permissions, "edit")
                settings[name] = CONVERTERS[kind](arguments[0])
                return {"status": "ok", "data": "ok", "discrete": True}
            return {"status": "ok", "data": settings[name], "discrete": False}
        if key == "general/toggleSelectionIsPlayhead":
            self._need(permissions, "edit")
            settings["lock_playhead_to_selection"] = settings["lock_playhead_to_selection"] == False
            return {"status": "ok", "data": "ok", "discrete": True}
        patches = {"audio/patchList": "audio", "mic/patchList": "audio_input", "midi/patchList": "midi",
                   "network/patchList": "network", "light/patch": "light", "video/stages": "video_stage",
                   "video/routes": "video_route"}
        if key in patches:
            if len(arguments) > 0:
                self._need(permissions, "edit")
                runtime.workspace.patches[patches[key]] = CONVERTERS["json"](arguments[0])
                return {"status": "ok", "data": "ok", "discrete": True}
            return {"status": "ok", "data": json.dumps(runtime.workspace.patches[patches[key]]), "discrete": False}
        if tail[-1:] in (["undo"], ["redo"]):
            self._need(permissions, "edit")
            getattr(runtime.workspace, tail[-1])()
            return {"status": "ok", "data": "ok", "discrete": True}
        raise ApiError("impostazione sconosciuta: " + key)
