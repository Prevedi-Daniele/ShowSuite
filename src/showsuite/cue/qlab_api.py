"""API OSC compatibile con QLab 5 (indirizzi, permessi, risposte JSON, wildcard, +/-, /live, push /update).

`QLabApi.handle(address, args, client)` è indipendente dal trasporto: usa `ClientHandle.send` per le risposte.
Vedi specs/SPEC-osc-qlab.md. Parti NON implementate sono elencate in `NOT_IMPLEMENTED`."""
from __future__ import annotations

import json
import re
import time

from .engine import ORIGIN_OSC, Runtime
from .model import (GROUP_PLAYLIST, COLORS, CUE_TYPES, TYPE_CART, TYPE_LIST, TYPE_GROUP, Cue, DuplicateNumberError,
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


CUE_EXTRA_NAMES = ("videoEffects", "videoEffect", "videoEffectIndex", "sliceMarker", "sliceMarkers", "addSliceMarker", "deleteSliceMarker", "deleteSliceMarkers", "playlist", "rotate", "audioOutputPatch", "audioOutputPatchID",
                   "audioOutputPatchName", "audioOutputPatchNumber", "muteChannels", "soloChannels",
                   "muteObjects", "soloObjects", "sliderLevel", "sliderLevels", "objectLevel", "objectIDLevel",
                   "objectLevels")
BROADCAST_CUE_EVENTS = ("go", "auditionGo", "cue/start", "cue/stop", "playhead")
BROADCAST_FORMS = ("args", "number", "name", "uniqueID", "type")
BROADCAST_NO_ARGUMENT_EVENTS = {"pause_all": "pauseAll", "resume_all": "resumeAll", "panic_all": "panicAll",
                                "stop_all": "stopAll", "hard_stop_all": "hardStopAll", "reset_all": "resetAll"}


class Session:
    def __init__(self):
        self.permissions: dict = {}
        self.always_reply = False
        self.reply_format = ""
        self.updates = False
        self.subscriptions: set = set()
        self.event_format = ""
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
        self._broadcast_event(runtime, name, cue, data)
        if name == "playhead":
            identifier = cue.unique_id if cue is not None else ""
            address = "/update/workspace/%s/cueList/%s/playbackPosition" % (runtime.workspace.workspace_id,
                                                                            data.get("list", ""))
            self._push(address, [identifier] if identifier != "" else [])

    # ------------------------------------------------------------------ show control broadcast (manuale 8.7)
    def _broadcast_event(self, runtime: Runtime, name: str, cue, data: dict) -> None:
        event = None
        if name == "start" and cue is not None:
            if data.get("by_go", False) == True:
                event = "auditionGo" if data.get("audition", False) == True else "go"
            else:
                event = "cue/start"
        elif name == "stop" and cue is not None:
            event = "cue/stop"
        elif name == "playhead" and cue is not None:
            event = "playhead"
        elif name in BROADCAST_NO_ARGUMENT_EVENTS:
            event = BROADCAST_NO_ARGUMENT_EVENTS[name]
        if event is None:
            return
        arguments = []
        if event in BROADCAST_CUE_EVENTS:
            arguments = [cue.number, cue.display_name(), cue.unique_id, TYPE_NAMES.get(cue.cue_type, cue.cue_type)]
        for session in list(self.sessions.values()):
            if len(session.subscriptions) == 0 or session.client is None:
                continue
            for form in BROADCAST_FORMS if event in BROADCAST_CUE_EVENTS else ("args",):
                if (event, form) not in session.subscriptions:
                    continue
                self._send_broadcast(session, event, form, arguments)

    @staticmethod
    def _send_broadcast(session: "Session", event: str, form: str, arguments: list) -> None:
        address = "/qlab/event/workspace/" + event
        if form == "args":
            payload = arguments
        else:
            address = address + "/" + form
            payload = [arguments[BROADCAST_FORMS.index(form) - 1]]
        if session.event_format != "":
            if form == "args" and len(arguments) > 0:
                return
            text = session.event_format.replace("#address#", address)
            text = text.replace("#data#", str(payload[0]) if len(payload) > 0 else "")
            text = text.replace("#status#", "ok").replace("#workspace_id#", "")
            parts = text.split(" ", 1)
            session.client.send(parts[0], [parts[1]] if len(parts) > 1 and parts[1] != "" else [])
            return
        session.client.send(address, payload)

    def _listen_command(self, address: str, arguments: list, session: Session):
        command = "listen" if address.startswith("/listen") else "ignore"
        rest = address[len("/" + command):].strip("/")
        wanted = self._broadcast_forms(rest)
        if wanted is None:
            return {"status": "error", "data": "evento show control sconosciuto", "discrete": False}
        if command == "listen":
            session.subscriptions |= wanted
        else:
            if rest == "":
                session.subscriptions.clear()
            else:
                session.subscriptions -= wanted
        return {"status": "ok", "data": "ok", "discrete": True}

    @staticmethod
    def _broadcast_forms(rest: str):
        every = set()
        for event in BROADCAST_CUE_EVENTS:
            for form in BROADCAST_FORMS:
                every.add((event, form))
        for event in BROADCAST_NO_ARGUMENT_EVENTS.values():
            every.add((event, "args"))
        if rest == "":
            return every
        parts = rest.split("/")
        detail = ""
        if parts[-1] in BROADCAST_FORMS[1:]:
            detail = parts[-1]
            parts = parts[:-1]
        event = "/".join(parts)
        if event in BROADCAST_CUE_EVENTS:
            if detail != "":
                return {(event, detail)}
            return {(event, form) for form in BROADCAST_FORMS}
        if event in BROADCAST_NO_ARGUMENT_EVENTS.values() and detail == "":
            return {(event, "args")}
        return None

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
        if address == "/listen" or address.startswith("/listen/") or address == "/ignore" or address.startswith("/ignore/"):
            return self._listen_command(address, arguments, session)
        if address == "/eventFormat":
            if len(arguments) > 0:
                session.event_format = str(arguments[0])
            return {"status": "ok", "data": session.event_format, "discrete": len(arguments) > 0}
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
        if name in CUE_EXTRA_NAMES or (name in ("mute", "solo") and len(subpath) > 0):
            return self._cue_extras(runtime, cues, parts, arguments, permissions, plural)
        if name in ("audioMap", "audioMapID", "audioMapName", "audioMapNumber", "object", "objectID", "objects"):
            return self._cue_object_audio(runtime, cues, parts, arguments, permissions, plural)
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
            runtime.stop_all()
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

    @staticmethod
    def ensure_patch_ids(runtime: Runtime) -> list:
        import uuid
        patches = runtime.workspace.patches["audio"]
        for entry in patches:
            if entry.get("unique_id", "") == "":
                entry["unique_id"] = str(uuid.uuid4()).upper()
        return patches

    @staticmethod
    def _patch_routing(entry: dict) -> list:
        first = int(entry.get("first_channel", 1))
        return list(range(first, first + int(entry.get("cue_outputs", entry.get("channels", 2)))))

    def _audio_patch_setting(self, runtime: Runtime, tail: list, arguments: list, permissions: set) -> dict:
        patches = self.ensure_patch_ids(runtime)
        reference = tail[2]
        entry = None
        for candidate in patches:
            if (tail[1] == "patch" and candidate.get("name", "") == reference) or \
                    (tail[1] == "patchID" and candidate["unique_id"] == reference):
                entry = candidate
        if entry is None:
            raise ApiError("patch audio non trovato")
        rest = tail[3:]
        ok = {"status": "ok", "data": "ok", "discrete": True}

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        def write_allowed():
            self._need(permissions, "edit")

        if rest == []:
            return read(json.dumps({"name": entry.get("name", ""), "uniqueID": entry["unique_id"],
                                    "routing": self._patch_routing(entry)}))
        head = rest[0]
        if head == "uniqueID":
            return read(entry["unique_id"])
        if head == "routing" and rest[1:] in ([], ["reset"]):
            return ok if rest[1:] == ["reset"] else read(self._patch_routing(entry))
        if head == "reset":
            return ok
        if head == "name":
            if len(arguments) > 0:
                write_allowed()
                entry["name"] = str(arguments[0])
                return ok
            return read(entry.get("name", ""))
        if head == "cueOutputChannels":
            if len(arguments) > 0:
                write_allowed()
                count = int(to_float(arguments[0]))
                if not 1 <= count <= 128:
                    raise ApiError("cueOutputChannels deve essere da 1 a 128")
                entry["cue_outputs"] = count
                return ok
            return read(int(entry.get("cue_outputs", entry.get("channels", 2))))
        if head in ("mute", "solo"):
            key = head
            channels = entry.setdefault(key, [])
            if rest[1:] == ["clear"]:
                write_allowed()
                channels.clear()
                return ok
            output = None
            if len(rest) > 1:
                output = int(to_float(rest[1]))
                value_arguments = arguments
            elif len(arguments) > 0:
                output = int(to_float(arguments[0]))
                value_arguments = arguments[1:]
            else:
                raise ApiError("manca il numero di uscita")
            if len(value_arguments) > 0:
                write_allowed()
                if to_bool(value_arguments[0]) == True:
                    if output not in channels:
                        channels.append(output)
                else:
                    if output in channels:
                        channels.remove(output)
                return ok
            return read(output in channels)
        if head in ("muteChannels", "soloChannels"):
            return read(sorted(entry.get(head[:4], [])))
        if head == "level" and len(rest) >= 3:
            levels = entry.setdefault("levels", {})
            crosspoint = "%d/%d" % (int(to_float(rest[1])), int(to_float(rest[2])))
            if len(arguments) > 0:
                write_allowed()
                levels[crosspoint] = -200.0 if isinstance(arguments[0], str) else to_float(arguments[0])
                return ok
            return read(levels.get(crosspoint, 0.0 if rest[1] == rest[2] else -200.0))
        raise ApiError("impostazione sconosciuta: " + "/".join(tail))

    # ------------------------------------------------------------------ audio map (manuale 5.6, dizionario 9.1)
    def _audio_map_setting(self, runtime: Runtime, tail: list, arguments: list, permissions: set) -> dict:
        from . import audiomap
        maps = runtime.workspace.patches.setdefault("audio_map", [])
        reference = tail[2]
        audio_map = None
        for candidate in maps:
            if (tail[1] == "map" and candidate["name"] == reference) or \
                    (tail[1] == "mapID" and candidate["unique_id"] == reference):
                audio_map = candidate
        if audio_map is None:
            raise ApiError("audio map non trovata")
        ok = {"status": "ok", "data": "ok", "discrete": True}
        rest = tail[3:]

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        if rest == []:
            return read(json.dumps(self._map_json(audio_map)))
        if rest == ["uniqueID"]:
            return read(audio_map["unique_id"])
        if rest[0] == "size":
            size = {"width": audio_map["width"], "height": audio_map["height"]}
            if rest == ["size"]:
                return read(json.dumps(size))
            if len(rest) == 2 and rest[1] in size:
                return read(size[rest[1]])
        for collection, key in (("filters", "filters"), ("marks", "marks"), ("objects", "objects")):
            if rest == [collection]:
                return read(json.dumps([self._map_item_json(item, key) for item in audio_map[key]]))
        if rest[0] == "testObject":
            return self._test_object(audio_map, rest[1:], arguments, permissions)
        kinds = {"filter": "filters", "filterID": "filters", "mark": "marks", "markID": "marks",
                 "object": "objects", "objectID": "objects"}
        if rest[0] in kinds and len(rest) >= 2:
            collection = kinds[rest[0]]
            items = self._match_map_items(audio_map[collection], rest[0], rest[1])
            if len(items) == 0:
                raise ApiError("elemento non trovato")
            results = [self._map_item_property(audio_map, collection, item, rest[2:], arguments, permissions)
                       for item in items]
            return results[0] if len(results) == 1 else {"status": "ok", "data": [item["data"] for item in results],
                                                          "discrete": results[0]["discrete"]}
        raise ApiError("impostazione sconosciuta: " + "/".join(tail))

    def _cue_object_audio(self, runtime: Runtime, cues: list, parts: list, arguments: list, permissions: set,
                          plural: bool) -> dict:
        """Proprietà di object audio di un cue: mappa in uso (audioMap*) e oggetti propri del cue (object*)."""
        from . import audiomap
        name = parts[0]
        maps = runtime.workspace.patches.setdefault("audio_map", [])
        collected = []
        for cue in cues:
            if cue.cue_type != "audio":
                raise ApiError("il cue non è di tipo Audio")
            if name in ("audioMapID", "audioMapName", "audioMapNumber"):
                reply = self._cue_map_reference(cue, maps, name, arguments, permissions)
            elif name == "audioMap":
                found = audiomap.find_map(maps, cue.params.get("audio_map", ""))
                if found is None:
                    raise ApiError("il cue non usa nessuna audio map")
                reply = self._audio_map_setting(runtime, ["audio", "mapID", found["unique_id"]] + parts[1:], arguments,
                                                permissions)
            else:
                reply = self._cue_own_objects(cue, parts, arguments, permissions)
            collected.append(reply)
        if len(collected) == 1 or plural == False:
            return collected[0]
        return {"status": "ok", "data": [item["data"] for item in collected], "discrete": collected[0]["discrete"]}

    # ------------------------------------------------------------------ proprietà aggiuntive dei cue
    def _cue_extras(self, runtime: Runtime, cues: list, parts: list, arguments: list, permissions: set,
                    plural: bool) -> dict:
        collected = []
        for cue in cues:
            collected.append(self._cue_extra_single(runtime, cue, parts, arguments, permissions))
        if len(collected) == 1 or plural == False:
            return collected[0]
        return {"status": "ok", "data": [item["data"] for item in collected], "discrete": collected[0]["discrete"]}

    def _video_effects(self, cue: Cue, name: str, rest: list, arguments: list, increment: int, writing: bool,
                       permissions: set) -> dict:
        """videoEffects (+ add/insert), videoEffect/{nome}/... e videoEffectIndex/{indice}/... (manuale 9.1)."""
        from . import videofx
        effects = cue.params.setdefault("video_fx", [])
        ok = {"status": "ok", "data": "ok", "discrete": True}

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        if name == "videoEffects":
            if len(rest) == 0:
                return read(json.dumps([effect["name"] for effect in effects]))
            self._need(permissions, "edit")
            try:
                effect = videofx.new_effect(str(arguments[0]))
            except (ValueError, IndexError) as error:
                raise ApiError(str(error))
            if rest[0] == "add":
                effects.append(effect)
            elif rest[0] == "insert":
                index = max(0, to_int(arguments[1])) if len(arguments) > 1 else len(effects)
                effects.insert(min(index, len(effects)), effect)
            else:
                raise ApiError("comando videoEffects sconosciuto: " + rest[0])
            return ok
        if len(rest) < 2:
            raise ApiError("effetto video non specificato")
        index = -1
        if name == "videoEffect":
            for position, effect in enumerate(effects):
                if effect["name"] == rest[0]:
                    index = position
                    break
        else:
            index = to_int(rest[0])
        action = rest[1]
        if not 0 <= index < len(effects):
            if action in ("delete", "move"):
                return ok
            raise ApiError("effetto video inesistente")
        effect = effects[index]
        if action == "delete":
            self._need(permissions, "edit")
            del effects[index]
            return ok
        if action == "move":
            self._need(permissions, "edit")
            target = min(max(0, to_int(arguments[0])), len(effects) - 1)
            effects.insert(target, effects.pop(index))
            return ok
        if action == "enabled":
            if len(arguments) == 0:
                return read(effect.get("enabled", True))
            self._need(permissions, "edit")
            effect["enabled"] = to_bool(arguments[0])
            return ok
        merged = dict(videofx.EFFECTS[effect["name"]]["parameters"])
        merged.update(effect["parameters"])
        if action == "parameters":
            if len(arguments) == 0:
                return read(json.dumps(merged))
            self._need(permissions, "edit")
            try:
                for key, value in json.loads(str(arguments[0])).items():
                    videofx.set_parameter(effect, key, value)
            except (ValueError, TypeError) as error:
                raise ApiError(str(error))
            return ok
        if action == "parameter" and len(rest) >= 3:
            key = rest[2]
            if key not in merged:
                raise ApiError("parametro sconosciuto: " + key)
            if len(arguments) == 0 and increment == 0:
                return read(merged[key])
            self._need(permissions, "edit")
            try:
                value = arguments if isinstance(merged[key], list) else arguments[0]
                if increment != 0:
                    value = float(merged[key]) + increment * to_float(arguments[0])
                videofx.set_parameter(effect, key, value)
            except (ValueError, TypeError, IndexError) as error:
                raise ApiError(str(error))
            return ok
        raise ApiError("comando effetto video sconosciuto: " + action)

    def _cue_extra_single(self, runtime: Runtime, cue: Cue, parts: list, arguments: list, permissions: set) -> dict:
        name = parts[0]
        ok = {"status": "ok", "data": "ok", "discrete": True}

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        increment = 0
        working = list(parts)
        if working[-1] in ("+", "-") and len(working) > 1:
            increment = 1 if working[-1] == "+" else -1
            working = working[:-1]
        if working[-1] == "live" and len(working) > 1:
            working = working[:-1]
        rest = working[1:]
        writing = len(arguments) > 0
        if writing == True:
            self._need(permissions, "edit")
        if name in ("addSliceMarker", "deleteSliceMarker", "deleteSliceMarkers"):
            self._need(permissions, "edit")
            slices = cue.params.setdefault("slices", [])
            if name == "deleteSliceMarkers":
                slices.clear()
            elif name == "deleteSliceMarker":
                index = int(to_float(rest[0] if len(rest) > 0 else arguments[0]))
                if not 0 <= index < len(slices):
                    raise ApiError("slice marker inesistente")
                del slices[index]
            else:
                when = to_float(arguments[0]) if len(arguments) > 0 else float(runtime.status(cue).get("action_elapsed", 0.0))
                count = to_int(arguments[1]) if len(arguments) > 1 else 1
                slices.append({"time": max(0.0, when), "play_count": "inf" if count < 0 else count})
                slices.sort(key=lambda item: float(item["time"]))
            return ok
        if name in ("videoEffects", "videoEffect", "videoEffectIndex"):
            return self._video_effects(cue, name, rest, arguments, increment, writing, permissions)
        if name in ("sliceMarker", "sliceMarkers"):
            return self._slice_markers(cue, name, rest, arguments, increment, writing)
        if name == "playlist":
            return self._playlist_property(runtime, cue, rest, arguments, permissions, writing)
        if name == "rotate":
            axes = {"x": 0, "y": 1, "z": 2}
            if len(rest) != 1 or rest[0] not in axes:
                raise ApiError("asse non valido")
            angles = cue.params.setdefault("rotate_euler", [0.0, 0.0, 0.0])
            if writing == True or increment != 0:
                value = to_float(arguments[0])
                angles[axes[rest[0]]] = angles[axes[rest[0]]] + increment * value if increment != 0 else value
                from .geometry import euler_to_quaternion
                cue.params["quaternion"] = euler_to_quaternion(*angles)
                return ok
            return read(angles[axes[rest[0]]])
        if name.startswith("audioOutputPatch"):
            return self._cue_output_patch(runtime, cue, name, rest, arguments, permissions)
        if name in ("mute", "solo", "muteChannels", "soloChannels", "muteObjects", "soloObjects"):
            return self._cue_mute_solo(cue, name, rest, arguments, writing)
        if name in ("sliderLevel", "sliderLevels"):
            levels = cue.params.setdefault("levels", {})
            if name == "sliderLevels":
                return read({key: value for key, value in levels.items() if key == "main" or key.startswith("slider/")})
            if len(rest) == 1 or (len(rest) == 0 and writing == True and len(arguments) == 2):
                channel = int(to_float(rest[0] if len(rest) == 1 else arguments[0]))
                values = arguments if len(rest) == 1 else arguments[1:]
            else:
                raise ApiError("manca il canale")
            key = "main" if channel == 0 else "slider/%d" % channel
            if len(values) > 0:
                levels[key] = -200.0 if isinstance(values[0], str) else to_float(values[0])
                return ok
            return read(levels.get(key, 0.0))
        if name in ("objectLevel", "objectIDLevel", "objectLevels"):
            levels = cue.params.setdefault("object_levels", {})
            if name == "objectLevels":
                return read(levels)
            if len(rest) != 2:
                raise ApiError("servono riga e oggetto")
            key = "%d/%s" % (int(to_float(rest[0])), rest[1])
            if writing == True:
                levels[key] = -200.0 if isinstance(arguments[0], str) else to_float(arguments[0])
                return ok
            return read(levels.get(key, 0.0))
        raise ApiError("proprietà sconosciuta: " + name)

    @staticmethod
    def _slice_markers(cue: Cue, name: str, rest: list, arguments: list, increment: int, writing: bool) -> dict:
        slices = cue.params.setdefault("slices", [])
        ok = {"status": "ok", "data": "ok", "discrete": True}

        def count_value(item):
            return -1 if item["play_count"] in ("inf", "infinite") else int(item["play_count"])

        def sort_slices():
            slices.sort(key=lambda item: float(item["time"]))

        if name == "sliceMarkers":
            if increment != 0:
                shift = increment * to_float(arguments[0])
                for item in slices:
                    item["time"] = max(0.0, float(item["time"]) + shift)
                return ok
            if writing == True:
                raise ApiError("sliceMarkers si scrive solo con + o -")
            return {"status": "ok", "discrete": False,
                    "data": json.dumps([{"time": item["time"], "playCount": count_value(item)} for item in slices])}
        values = list(arguments)
        if len(rest) == 0:
            if len(values) == 0:
                raise ApiError("manca l'indice")
            rest = [str(int(to_float(values.pop(0))))]
        index = int(to_float(rest[0]))
        if not 0 <= index < len(slices):
            raise ApiError("slice marker inesistente")
        field = rest[1] if len(rest) > 1 else ""
        if len(values) == 0:
            item = slices[index]
            if field == "time":
                return {"status": "ok", "data": item["time"], "discrete": False}
            if field == "playCount":
                return {"status": "ok", "data": count_value(item), "discrete": False}
            return {"status": "ok", "discrete": False,
                    "data": json.dumps({"time": item["time"], "playCount": count_value(item)})}
        if field == "time":
            slices[index]["time"] = max(0.0, to_float(values[0]))
        elif field == "playCount":
            slices[index]["play_count"] = "inf" if to_int(values[0]) < 0 else to_int(values[0])
        else:
            if len(values) < 2:
                raise ApiError("servono tempo e play count")
            slices[index] = {"time": max(0.0, to_float(values[0])),
                             "play_count": "inf" if to_int(values[1]) < 0 else to_int(values[1])}
        sort_slices()
        return ok

    def _playlist_property(self, runtime: Runtime, cue: Cue, rest: list, arguments: list, permissions: set,
                           writing: bool) -> dict:
        ok = {"status": "ok", "data": "ok", "discrete": True}
        if cue.cue_type != "group" or cue.group_mode() != GROUP_PLAYLIST:
            return ok if writing == True or rest in (["next"], ["previous"]) else {"status": "ok", "data": False,
                                                                                    "discrete": False}
        flags = {"doCrossfade": "playlist_crossfade", "doLoop": "playlist_loop", "doShuffle": "playlist_shuffle"}
        if len(rest) == 1 and rest[0] in flags:
            if writing == True:
                cue.params[flags[rest[0]]] = to_bool(arguments[0])
                return ok
            return {"status": "ok", "data": cue.params.get(flags[rest[0]], False), "discrete": False}
        if rest == ["crossfade", "duration"]:
            if writing == True:
                value = to_float(arguments[0])
                if value < 0:
                    raise ApiError("la durata non può essere negativa")
                cue.params["playlist_crossfade_duration"] = value
                return ok
            return {"status": "ok", "data": cue.params.get("playlist_crossfade_duration", 0.05), "discrete": False}
        if rest in (["next"], ["previous"]):
            self._need(permissions, "control")
            runtime.playlist_step(cue, 1 if rest == ["next"] else -1)
            return ok
        if rest in (["currentCue"], ["currentCueID"]):
            current = None
            for child in runtime._ordered_children(cue):
                state = runtime.states.get(child.unique_id)
                if state is not None and state.action_running == True and state.crossfading_out == False:
                    current = child
            if writing == True:
                self._need(permissions, "control")
                for child in runtime._ordered_children(cue):
                    if str(arguments[0]) in (child.number, child.unique_id):
                        runtime.start_cue(child, origin=ORIGIN_OSC)
                return ok
            if current is None:
                return {"status": "ok", "data": "", "discrete": False}
            return {"status": "ok", "data": current.number if rest == ["currentCue"] else current.unique_id,
                    "discrete": False}
        raise ApiError("proprietà sconosciuta: playlist/" + "/".join(rest))

    def _cue_output_patch(self, runtime: Runtime, cue: Cue, name: str, rest: list, arguments: list,
                          permissions: set) -> dict:
        patches = self.ensure_patch_ids(runtime)
        number = int(cue.params.get("audio_output_patch", 1))
        current = patches[number - 1] if 1 <= number <= len(patches) else None
        writing = len(arguments) > 0
        if name == "audioOutputPatch":
            if current is None:
                raise ApiError("il cue non è collegato a una patch audio")
            return self._audio_patch_setting(runtime, ["audio", "patchID", current["unique_id"]] + rest, arguments,
                                             permissions)
        if writing == False:
            data = {"audioOutputPatchID": current["unique_id"] if current else "",
                    "audioOutputPatchName": current["name"] if current else "none",
                    "audioOutputPatchNumber": number if current else 0}[name]
            return {"status": "ok", "data": data, "discrete": False}
        value = arguments[0]
        chosen = None
        if name == "audioOutputPatchNumber":
            if int(to_float(value)) == 0:
                chosen = 0
            elif 1 <= int(to_float(value)) <= len(patches):
                chosen = int(to_float(value))
        elif str(value) in ("", "none"):
            chosen = 0
        else:
            key = "unique_id" if name == "audioOutputPatchID" else "name"
            for index, entry in enumerate(patches):
                if entry.get(key) == str(value):
                    chosen = index + 1
        if chosen is not None:
            cue.params["audio_output_patch"] = chosen
        return {"status": "ok", "data": "ok", "discrete": True}

    @staticmethod
    def _cue_mute_solo(cue: Cue, name: str, rest: list, arguments: list, writing: bool) -> dict:
        kind = "mute" if name.startswith("mute") else "solo"
        state = cue.params.setdefault(kind + "_outputs", {"channels": [], "objects": []})
        ok = {"status": "ok", "data": "ok", "discrete": True}
        if name.endswith("Channels"):
            return {"status": "ok", "data": sorted(state["channels"]), "discrete": False}
        if name.endswith("Objects"):
            return {"status": "ok", "data": list(state["objects"]), "discrete": False}
        if rest == ["clear"]:
            state["channels"].clear()
            state["objects"].clear()
            return ok
        if rest[:1] == ["channel"] and rest[1:] == ["clear"]:
            state["channels"].clear()
            return ok
        if rest[:1] == ["object"] and rest[1:] == ["clear"]:
            state["objects"].clear()
            return ok
        if rest[:1] in (["object"], ["objectID"]) and len(rest) == 2:
            target, group = rest[1], state["objects"]
        elif rest[:1] == ["channel"] and len(rest) == 2:
            target, group = int(to_float(rest[1])), state["channels"]
        elif len(rest) == 1:
            target, group = int(to_float(rest[0])), state["channels"]
        else:
            raise ApiError("proprietà sconosciuta: " + name + "/" + "/".join(rest))
        if writing == True:
            if to_bool(arguments[0]) == True and target not in group:
                group.append(target)
            elif to_bool(arguments[0]) == False and target in group:
                group.remove(target)
            return ok
        return {"status": "ok", "data": target in group, "discrete": False}

    def _cue_map_reference(self, cue: Cue, maps: list, name: str, arguments: list, permissions: set) -> dict:
        current = None
        for audio_map in maps:
            if audio_map["unique_id"] == cue.params.get("audio_map", "") or audio_map["name"] == cue.params.get("audio_map", ""):
                current = audio_map
        if len(arguments) == 0:
            if name == "audioMapID":
                return {"status": "ok", "data": current["unique_id"] if current else "", "discrete": False}
            if name == "audioMapName":
                return {"status": "ok", "data": current["name"] if current else "", "discrete": False}
            return {"status": "ok", "data": maps.index(current) + 1 if current else 0, "discrete": False}
        self._need(permissions, "edit")
        value = arguments[0]
        chosen = ""
        if name == "audioMapNumber":
            index = int(to_float(value))
            if index != 0:
                if not 1 <= index <= len(maps):
                    raise ApiError("audio map non trovata")
                chosen = maps[index - 1]["unique_id"]
        elif str(value) not in ("", "none"):
            key = "unique_id" if name == "audioMapID" else "name"
            matches = [audio_map for audio_map in maps if audio_map[key] == str(value)]
            if len(matches) == 0:
                raise ApiError("audio map non trovata")
            chosen = matches[0]["unique_id"]
        cue.params["audio_map"] = chosen
        return {"status": "ok", "data": "ok", "discrete": True}

    def _cue_own_objects(self, cue: Cue, parts: list, arguments: list, permissions: set) -> dict:
        import uuid
        objects = cue.params.setdefault("objects", [])
        for index, entry in enumerate(objects):
            entry.setdefault("unique_id", str(uuid.uuid4()).upper())
            entry.setdefault("name", chr(ord("A") + index % 26) * (index // 26 + 1))
            entry.setdefault("x", 0.0)
            entry.setdefault("y", 0.0)
            entry.setdefault("spread", 0.0)
            entry.setdefault("color", "none")
        if parts == ["objects"]:
            return {"status": "ok", "data": json.dumps([self._map_item_json(entry, "objects") for entry in objects]),
                    "discrete": False}
        if len(parts) < 2 or parts[0] not in ("object", "objectID"):
            raise ApiError("proprietà sconosciuta: " + "/".join(parts))
        items = self._match_map_items(objects, parts[0], parts[1])
        if len(items) == 0:
            raise ApiError("oggetto non trovato")
        return self._map_item_property({"width": 1000.0, "height": 1000.0}, "objects", items[0], parts[2:], arguments,
                                       permissions)

    @staticmethod
    def _match_map_items(items: list, kind: str, reference: str) -> list:
        if kind.endswith("ID"):
            return [item for item in items if item["unique_id"] == reference]
        return [item for item in items if pattern_matches(reference, item["name"])]

    @staticmethod
    def _levels_list(mark: dict) -> list:
        return [mark["levels"].get(output, -200.0) for output in range(0, 129)]

    def _map_item_json(self, item: dict, collection: str) -> dict:
        data = {"name": item["name"], "uniqueID": item["unique_id"], "x": item["x"], "y": item["y"]}
        if collection == "marks":
            data.update({"gravity": item["gravity"], "shadow": item["shadow"], "levels": self._levels_list(item)})
        elif collection == "filters":
            data.update({"angle": item["angle"], "width": item["width"],
                         "passthroughs": [output in item["passthroughs"] for output in range(1, 129)]})
        else:
            data.update({"spread": item["spread"], "colorName": item["color"]})
        return data

    def _map_json(self, audio_map: dict) -> dict:
        return {"uniqueID": audio_map["unique_id"], "name": audio_map["name"], "width": audio_map["width"],
                "height": audio_map["height"],
                "filters": [self._map_item_json(item, "filters") for item in audio_map["filters"]],
                "marks": [self._map_item_json(item, "marks") for item in audio_map["marks"]],
                "objects": [self._map_item_json(item, "objects") for item in audio_map["objects"]]}

    def _map_item_property(self, audio_map: dict, collection: str, item: dict, rest: list, arguments: list,
                           permissions: set) -> dict:
        ok = {"status": "ok", "data": "ok", "discrete": True}

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        if len(rest) > 0 and rest[-1] == "live":
            rest = rest[:-1]
        if rest == []:
            return read(json.dumps(self._map_item_json(item, collection)))
        head = rest[0]
        if head == "uniqueID":
            return read(item["unique_id"])
        writing = len(arguments) > 0
        if writing == True:
            self._need(permissions, "edit")
        if head == "name":
            if writing == True:
                item["name"] = str(arguments[0])
                return ok
            return read(item["name"])
        if head == "position":
            if rest == ["position"]:
                if writing == True:
                    item["x"], item["y"] = to_float(arguments[0]), to_float(arguments[1])
                    return ok
                return read([item["x"], item["y"]])
            if len(rest) == 2 and rest[1] in ("x", "y"):
                if writing == True:
                    item[rest[1]] = to_float(arguments[0])
                    return ok
                return read(item[rest[1]])
        ranges = {("marks", "gravity"): (0.1, 5.0), ("marks", "shadow"): (0.0, 90.0),
                  ("filters", "angle"): (-180.0, 180.0), ("objects", "spread"): (0.0, float("inf"))}
        if (collection, head) in ranges:
            low, high = ranges[(collection, head)]
            if writing == True:
                value = to_float(arguments[0])
                if not low <= value <= high:
                    raise ApiError("%s deve essere tra %s e %s" % (head, low, high))
                item[head] = value
                return ok
            return read(item[head])
        if collection == "filters" and head == "width":
            if writing == True:
                value = to_float(arguments[0])
                if value < 0 or value > max(audio_map["width"], audio_map["height"]) / 2.0:
                    raise ApiError("larghezza del filtro non valida")
                item["width"] = value
                return ok
            return read(item["width"])
        if collection == "filters" and head == "passthroughs":
            return read([output in item["passthroughs"] for output in range(1, 129)])
        if collection == "filters" and head == "passthrough" and len(rest) == 2:
            output = int(to_float(rest[1]))
            if not 1 <= output <= 128:
                raise ApiError("uscita da 1 a 128")
            if writing == True:
                if to_bool(arguments[0]) == True and output not in item["passthroughs"]:
                    item["passthroughs"] = sorted(item["passthroughs"] + [output])
                elif to_bool(arguments[0]) == False and output in item["passthroughs"]:
                    item["passthroughs"].remove(output)
                return ok
            return read(output in item["passthroughs"])
        if collection == "marks" and head == "levels":
            return read(self._levels_list(item))
        if collection == "marks" and head == "level" and len(rest) == 2:
            output = int(to_float(rest[1]))
            if not 0 <= output <= 128:
                raise ApiError("uscita da 0 a 128")
            if writing == True:
                item["levels"][output] = -200.0 if isinstance(arguments[0], str) else to_float(arguments[0])
                return ok
            return read(item["levels"].get(output, -200.0))
        if collection == "objects" and head == "colorName":
            from .audiomap import COLORS as map_colors
            if writing == True:
                if str(arguments[0]) not in map_colors:
                    raise ApiError("colore sconosciuto")
                item["color"] = str(arguments[0])
                return ok
            return read(item["color"])
        raise ApiError("impostazione sconosciuta: " + "/".join(rest))

    def _test_object(self, audio_map: dict, rest: list, arguments: list, permissions: set) -> dict:
        test = audio_map["test_object"]
        ok = {"status": "ok", "data": "ok", "discrete": True}
        if rest == []:
            return {"status": "ok", "data": json.dumps(test), "discrete": False}
        if rest in (["start"], ["stop"]):
            self._need(permissions, "control")
            test["running"] = rest == ["start"]
            return ok
        names = {("running",): "running", ("level",): "level"}
        if rest == ["running"]:
            return {"status": "ok", "data": test["running"], "discrete": False}
        if rest == ["level"]:
            if len(arguments) > 0:
                self._need(permissions, "control")
                test["level"] = -200.0 if isinstance(arguments[0], str) else to_float(arguments[0])
                return ok
            return {"status": "ok", "data": test["level"], "discrete": False}
        if rest == ["position"]:
            if len(arguments) >= 2:
                self._need(permissions, "control")
                test["x"], test["y"] = to_float(arguments[0]), to_float(arguments[1])
                return ok
            return {"status": "ok", "data": [test["x"], test["y"]], "discrete": False}
        if len(rest) == 2 and rest[0] == "position" and rest[1] in ("x", "y"):
            if len(arguments) > 0:
                self._need(permissions, "control")
                test[rest[1]] = to_float(arguments[0])
                return ok
            return {"status": "ok", "data": test[rest[1]], "discrete": False}
        raise ApiError("impostazione sconosciuta: testObject/" + "/".join(rest))

    @staticmethod
    def ensure_video_ids(runtime: Runtime) -> None:
        import uuid
        for kind in ("video_stage", "video_route"):
            for entry in runtime.workspace.patches[kind]:
                if entry.get("unique_id", "") == "":
                    entry["unique_id"] = str(uuid.uuid4()).upper()
        for stage in runtime.workspace.patches["video_stage"]:
            for region in stage.get("regions", []):
                if region.get("unique_id", "") == "":
                    region["unique_id"] = str(uuid.uuid4()).upper()

    @staticmethod
    def _pick_item(items: list, kind: str, reference: str, label: str) -> dict:
        """Seleziona per nome, per ID o per indice (da 0) un elemento di una lista di patch."""
        for index, item in enumerate(items):
            if kind.endswith("ID") and item.get("unique_id") == reference:
                return item
            if kind.endswith("Index") and str(index) == reference:
                return item
            if kind in ("stage", "route", "region") and item.get("name") == reference:
                return item
        raise ApiError(label + " non trovato")

    def _video_setting(self, runtime: Runtime, tail: list, arguments: list, permissions: set) -> dict:
        self.ensure_video_ids(runtime)
        ok = {"status": "ok", "data": "ok", "discrete": True}
        patches = runtime.workspace.patches

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        if tail[1].startswith("route"):
            route = self._pick_item(patches["video_route"], tail[1], tail[2], "route video")
            rest = tail[3:]
            if rest == []:
                return read(json.dumps({"enableGuides": route.get("enable_guides", False), "name": route.get("name", ""),
                                        "uniqueID": route["unique_id"], "rotationDegrees": route.get("rotation", 0),
                                        "scalingMode": route.get("scaling_mode", 0), "rear": route.get("rear", False)}))
            if rest == ["uniqueID"]:
                return read(route["unique_id"])
            if rest == ["enableGuides"]:
                if len(arguments) > 0:
                    self._need(permissions, "edit")
                    route["enable_guides"] = to_bool(arguments[0])
                    return ok
                return read(route.get("enable_guides", False))
            raise ApiError("impostazione sconosciuta: " + "/".join(tail))
        stage = self._pick_item(patches["video_stage"], tail[1], tail[2], "stage")
        stage_height = int(stage.get("height", 1080))
        stage_width = int(stage.get("width", 1920))
        rest = tail[3:]
        if rest == []:
            return read(json.dumps(self._stage_json(stage)))
        if rest == ["uniqueID"]:
            return read(stage["unique_id"])
        if rest == ["name"]:
            if len(arguments) > 0:
                self._need(permissions, "edit")
                stage["name"] = str(arguments[0])
                return ok
            return read(stage.get("name", ""))
        if rest == ["regions"]:
            return read(json.dumps([self._region_json(region, stage_height) for region in stage.get("regions", [])]))
        if rest[0] == "size":
            size = {"width": stage_width, "height": stage_height}
            if rest == ["size"]:
                return read(json.dumps(size))
            if len(rest) == 2 and rest[1] in size:
                return read(size[rest[1]])
        if rest[0] in ("region", "regionID", "regionIndex") and len(rest) >= 2:
            region = self._pick_item(stage.get("regions", []), rest[0], rest[1], "regione")
            return self._region_setting(region, rest[2:], arguments, permissions, stage_width, stage_height)
        raise ApiError("impostazione sconosciuta: " + "/".join(tail))

    @staticmethod
    def _bounds_api(region: dict, stage_height: int) -> dict:
        x, y, width, height = [int(value) for value in region.get("bounds", [0, 0, 0, 0])]
        return {"x": x, "y": stage_height - y - height, "width": width, "height": height}

    def _region_json(self, region: dict, stage_height: int) -> dict:
        return {"name": region.get("name", ""), "uniqueID": region["unique_id"],
                "boundsOnStage": self._bounds_api(region, stage_height), "meshWidth": 2, "meshHeight": 2,
                "warpType": 0, "controlPoints": region.get("control_points_list", [])}

    def _stage_json(self, stage: dict) -> dict:
        height = int(stage.get("height", 1080))
        return {"uniqueID": stage["unique_id"], "name": stage.get("name", ""), "width": int(stage.get("width", 1920)),
                "height": height, "regions": [self._region_json(region, height) for region in stage.get("regions", [])]}

    def _region_setting(self, region: dict, rest: list, arguments: list, permissions: set, stage_width: int,
                        stage_height: int) -> dict:
        ok = {"status": "ok", "data": "ok", "discrete": True}

        def read(value):
            return {"status": "ok", "data": value, "discrete": False}

        if rest == []:
            return read(json.dumps(self._region_json(region, stage_height)))
        if rest == ["enableGrid"] or rest == ["enableGuide"]:
            key = "enable_grid" if rest == ["enableGrid"] else "enable_guide"
            if len(arguments) > 0:
                self._need(permissions, "edit")
                region[key] = to_bool(arguments[0])
                return ok
            return read(region.get(key, False))
        if rest == ["resetControlPoints"]:
            self._need(permissions, "edit")
            region.pop("warp", None)
            region.pop("control_points", None)
            return ok
        if rest[0] == "subregionIndex" and len(rest) == 4 and rest[2] == "controlPointIndex":
            points = region.setdefault("control_points", {})
            key = "%s/%s" % (rest[1], rest[3])
            if len(arguments) >= 2:
                self._need(permissions, "edit")
                points[key] = [to_float(arguments[0]), to_float(arguments[1])]
                return ok
            return read(json.dumps(points.get(key, [0.0, 0.0])))
        if rest[0] == "bounds":
            current = self._bounds_api(region, stage_height)
            part = rest[1:]
            if len(arguments) == 0:
                if part == []:
                    return read(json.dumps(current))
                if part == ["origin"]:
                    return read(json.dumps({"x": current["x"], "y": current["y"]}))
                if part == ["size"]:
                    return read(json.dumps({"width": current["width"], "height": current["height"]}))
                if len(part) == 1 and part[0] in current:
                    return read(current[part[0]])
                if len(part) == 2 and part[1] in current:
                    return read(current[part[1]])
                raise ApiError("impostazione sconosciuta: bounds/" + "/".join(part))
            self._need(permissions, "edit")
            numbers = self._parse_bounds_arguments(arguments)
            if part == []:
                current.update(zip(("x", "y", "width", "height"), numbers))
            elif part == ["origin"]:
                current["x"], current["y"] = numbers[0], numbers[1]
            elif part == ["size"]:
                current["width"], current["height"] = numbers[0], numbers[1]
            elif len(part) == 2 and part[1] in current:
                current[part[1]] = numbers[0]
            else:
                raise ApiError("impostazione sconosciuta: bounds/" + "/".join(part))
            if current["x"] < 0 or current["y"] < 0 or current["width"] <= 0 or current["height"] <= 0 or \
                    current["x"] + current["width"] > stage_width or current["y"] + current["height"] > stage_height:
                raise ApiError("la regione deve stare dentro lo stage")
            region["bounds"] = [current["x"], stage_height - current["y"] - current["height"], current["width"],
                                current["height"]]
            return ok
        raise ApiError("impostazione sconosciuta: " + "/".join(rest))

    @staticmethod
    def _parse_bounds_arguments(arguments: list) -> list:
        if len(arguments) == 1 and isinstance(arguments[0], str):
            found = re.findall(r"-?\d+", arguments[0])
            if len(found) not in (1, 2, 4):
                raise ApiError("formato dei bounds non valido")
            return [int(value) for value in found]
        values = []
        for value in arguments:
            number = to_float(value)
            if number != int(number):
                raise ApiError("i valori devono essere interi")
            values.append(int(number))
        return values

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
        if len(tail) >= 3 and tail[0] == "audio" and tail[1] in ("patch", "patchID"):
            return self._audio_patch_setting(runtime, tail, arguments, permissions)
        if len(tail) >= 3 and tail[0] == "audio" and tail[1] in ("map", "mapID"):
            return self._audio_map_setting(runtime, tail, arguments, permissions)
        if len(tail) >= 3 and tail[0] == "video" and tail[1] in ("stage", "stageID", "route", "routeID", "routeIndex"):
            return self._video_setting(runtime, tail, arguments, permissions)
        if tail[-1:] in (["undo"], ["redo"]):
            self._need(permissions, "edit")
            getattr(runtime.workspace, tail[-1])()
            return {"status": "ok", "data": "ok", "discrete": True}
        raise ApiError("impostazione sconosciuta: " + key)
