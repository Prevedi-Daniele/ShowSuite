"""Compositor video software: stage -> regions -> route -> uscita, maschere, edge blend, warp prospettico.

Pipeline: ogni Video/Camera/Text cue attivo è un `VideoLayer` disegnato sul canvas dello stage (ordine per `layer`,
modi di fusione normal/add/multiply/screen, opacità, crop, scala/traslazione/rotazione 3D con quaternione, anchor).
Le regioni ritagliano lo stage; ogni route manda una regione a un dispositivo (`FrameSink`).
Richiede numpy + opencv. Approssimazioni dichiarate: warp solo prospettico a 4 angoli (no lineare/Bézier a griglia),
video effects non implementati, Syphon (solo macOS) sostituito da `FrameSink` (finestra Qt / file; NDI e Spout NON
implementati), Camera usa cv2.VideoCapture. Riproduzione NON provata su proiettori reali."""
from __future__ import annotations

import math

import cv2
import numpy as np

from .engine import ActionHandler, CueState, Runtime
from .model import TYPE_CAMERA, TYPE_TEXT, TYPE_VIDEO, Cue


def quaternion_to_matrix(quaternion) -> np.ndarray:
    w, x, y, z = [float(value) for value in quaternion]
    norm = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def euler_to_quaternion(x_degrees: float, y_degrees: float, z_degrees: float) -> list[float]:
    cx, sx = math.cos(math.radians(x_degrees) / 2), math.sin(math.radians(x_degrees) / 2)
    cy, sy = math.cos(math.radians(y_degrees) / 2), math.sin(math.radians(y_degrees) / 2)
    cz, sz = math.cos(math.radians(z_degrees) / 2), math.sin(math.radians(z_degrees) / 2)
    return [cx * cy * cz + sx * sy * sz, sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz]


class FrameSink:
    def send(self, route_name: str, frame: np.ndarray) -> None:
        raise NotImplementedError


class MemorySink(FrameSink):
    def __init__(self):
        self.frames: dict[str, np.ndarray] = {}

    def send(self, route_name: str, frame: np.ndarray) -> None:
        self.frames[route_name] = frame


class FileSink(FrameSink):
    """Salva l'ultimo frame di ogni route come PNG (utile senza proiettore)."""

    def __init__(self, directory: str):
        self.directory = directory

    def send(self, route_name: str, frame: np.ndarray) -> None:
        import os
        os.makedirs(self.directory, exist_ok=True)
        cv2.imwrite(os.path.join(self.directory, route_name + ".png"), cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA))


class MediaSource:
    """Sorgente di frame RGBA: immagine fissa, video (seek per tempo) o webcam."""

    def __init__(self, path: str, camera_index: int | None = None):
        self.path = path
        self.capture = None
        self.image: np.ndarray | None = None
        self.last_time = -1.0
        self.last_frame: np.ndarray | None = None
        if camera_index is not None:
            self.capture = cv2.VideoCapture(camera_index)
        else:
            image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if image is not None:
                self.image = self._to_rgba(image)
            else:
                self.capture = cv2.VideoCapture(path)

    @staticmethod
    def _to_rgba(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGRA)
        elif frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)

    def duration(self) -> float | None:
        if self.capture is None or self.image is not None:
            return None
        frames = self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
        rate = self.capture.get(cv2.CAP_PROP_FPS) or 25.0
        return frames / rate if frames > 0 else None

    def frame_at(self, seconds: float) -> np.ndarray | None:
        if self.image is not None:
            return self.image
        if self.capture is None:
            return None
        if self.last_frame is not None and abs(seconds - self.last_time) < 1e-3:
            return self.last_frame
        if self.path != "" and self.last_time >= 0 and 0 <= seconds - self.last_time < 0.5:
            pass
        else:
            self.capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000.0)
        ok, frame = self.capture.read()
        if ok == False:
            return self.last_frame
        self.last_time = seconds
        self.last_frame = self._to_rgba(frame)
        return self.last_frame

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()


def render_text(cue: Cue) -> np.ndarray:
    fmt = cue.params.get("format", {})
    lines = str(cue.params.get("text", "")).split("\n")
    size = float(fmt.get("font_size", 48.0))
    scale = size / 30.0
    thickness = max(1, int(scale * 1.5)) if fmt.get("bold", False) else max(1, int(scale))
    color = [int(255 * channel) for channel in fmt.get("color", [1.0, 1.0, 1.0, 1.0])]
    widths = []
    height = int(size * 1.4)
    for line in lines:
        (width, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        widths.append(width)
    canvas = np.zeros((height * max(1, len(lines)) + 10, max(widths + [10]) + 20, 4), dtype=np.uint8)
    for index, line in enumerate(lines):
        offset = (canvas.shape[1] - widths[index]) // 2 if fmt.get("alignment", "center") == "center" else 10
        cv2.putText(canvas, line, (offset, int(size * 1.1) + index * height), cv2.FONT_HERSHEY_SIMPLEX, scale,
                    (color[0], color[1], color[2], 255), thickness, cv2.LINE_AA)
    return canvas


def blend(destination: np.ndarray, source_rgb: np.ndarray, alpha: np.ndarray, mode: str) -> np.ndarray:
    dest_rgb = destination[..., :3].astype(np.float32) / 255.0
    src = source_rgb.astype(np.float32) / 255.0
    if mode == "add":
        mixed = np.clip(dest_rgb + src, 0, 1)
    elif mode == "multiply":
        mixed = dest_rgb * src
    elif mode == "screen":
        mixed = 1 - (1 - dest_rgb) * (1 - src)
    else:
        mixed = src
    weight = alpha[..., None]
    out_rgb = dest_rgb * (1 - weight) + mixed * weight
    out_alpha = np.clip(destination[..., 3:4] / 255.0 + weight * (1 - destination[..., 3:4] / 255.0), 0, 1)
    destination[..., :3] = (out_rgb * 255).astype(np.uint8)
    destination[..., 3:4] = (out_alpha * 255).astype(np.uint8)
    return destination


class VideoCompositor(ActionHandler):
    def __init__(self, runtime: Runtime, sink: FrameSink | None = None, perspective_distance: float = 2.5):
        self.runtime = runtime
        self.sink = sink if sink is not None else MemorySink()
        self.sources: dict[str, MediaSource] = {}
        self.perspective_distance = perspective_distance

    def install(self) -> None:
        for cue_type in (TYPE_VIDEO, TYPE_CAMERA, TYPE_TEXT):
            self.runtime.register_handler(cue_type, self)

    # --- handler ---
    def _source_for(self, cue: Cue) -> MediaSource | None:
        if cue.cue_type == TYPE_TEXT:
            return None
        if cue.unique_id not in self.sources:
            if cue.cue_type == TYPE_CAMERA:
                self.sources[cue.unique_id] = MediaSource("", camera_index=int(cue.params.get("video_input_patch", 1)) - 1)
            else:
                self.sources[cue.unique_id] = MediaSource(cue.params.get("file_target", ""))
        return self.sources[cue.unique_id]

    def load(self, runtime, cue: Cue, seconds) -> None:
        self._source_for(cue)

    def stop(self, runtime, state: CueState, hard: bool) -> None:
        cue = state.cue
        if cue.params.get("hold_last_frame", False) == True and hard == False and state.action_elapsed >= \
                state.action_duration - 1e-6 and state.action_duration != math.inf:
            return
        source = self.sources.pop(cue.unique_id, None)
        if source is not None:
            source.release()

    # --- stage ---
    def stage_definition(self, number: int) -> dict:
        stages = self.runtime.workspace.patches["video_stage"]
        if 1 <= number <= len(stages):
            return stages[number - 1]
        return {"name": "Stage", "width": 1920, "height": 1080, "regions": []}

    def active_layers(self) -> list[tuple[Cue, float]]:
        layers = []
        for state in self.runtime.states.values():
            cue = state.cue
            if cue.cue_type not in (TYPE_VIDEO, TYPE_CAMERA, TYPE_TEXT) or state.action_running == False:
                continue
            if state.virtual == True or state.paused == True and False:
                continue
            layers.append((cue, state.action_elapsed))
        layers.sort(key=lambda item: int(self.runtime.get_param(item[0], "layer", 0)))
        return layers

    def render_stage(self, number: int = 1) -> np.ndarray:
        stage = self.stage_definition(number)
        width, height = int(stage["width"]), int(stage["height"])
        canvas = np.zeros((height, width, 4), dtype=np.uint8)
        canvas[..., 3] = 255
        for cue, elapsed in self.active_layers():
            if int(self.runtime.get_param(cue, "stage", 1)) != number:
                continue
            self._draw_layer(canvas, cue, elapsed)
        return canvas

    def _layer_frame(self, cue: Cue, elapsed: float) -> np.ndarray | None:
        if cue.cue_type == TYPE_TEXT:
            return render_text(cue)
        source = self._source_for(cue)
        rate = float(self.runtime.get_param(cue, "rate", 1.0))
        return source.frame_at(float(cue.params.get("start_time", 0.0)) + elapsed * rate) if source is not None else None

    def _draw_layer(self, canvas: np.ndarray, cue: Cue, elapsed: float) -> None:
        frame = self._layer_frame(cue, elapsed)
        if frame is None:
            return
        get = lambda name, default: self.runtime.get_param(cue, name, default)
        top, bottom, left, right = [float(value) for value in get("crop", [0, 0, 0, 0])]
        height_px, width_px = frame.shape[:2]
        frame = frame[int(top):height_px - int(bottom), int(left):width_px - int(right)]
        if frame.size == 0:
            return
        stage_height, stage_width = canvas.shape[:2]
        source_height, source_width = frame.shape[:2]
        scale_x, scale_y = [float(value) for value in get("scale", [1.0, 1.0])]
        base_x = base_y = 1.0
        if get("fill_stage", True) == True:
            if get("preserve_aspect_ratio", True) == True:
                fit = min(stage_width / source_width, stage_height / source_height)
                base_x = base_y = fit
            else:
                base_x, base_y = stage_width / source_width, stage_height / source_height
        draw_width = source_width * base_x * scale_x
        draw_height = source_height * base_y * scale_y
        translation_x, translation_y = [float(value) for value in get("translation", [0.0, 0.0])]
        anchor_x, anchor_y = [float(value) for value in get("anchor", [0.0, 0.0])]
        center = np.array([stage_width / 2 + translation_x, stage_height / 2 - translation_y, 0.0])
        corners = np.array([[-draw_width / 2, -draw_height / 2, 0], [draw_width / 2, -draw_height / 2, 0],
                            [draw_width / 2, draw_height / 2, 0], [-draw_width / 2, draw_height / 2, 0]], dtype=np.float64)
        pivot = np.array([anchor_x * draw_width / 2, -anchor_y * draw_height / 2, 0.0])
        rotation = quaternion_to_matrix(get("quaternion", [1.0, 0.0, 0.0, 0.0]))
        rotated = (corners - pivot) @ rotation.T + pivot
        distance = self.perspective_distance * max(stage_width, stage_height)
        projected = []
        for point in rotated:
            factor = distance / max(1.0, distance - point[2])
            projected.append([center[0] + point[0] * factor, center[1] + point[1] * factor])
        source_points = np.array([[0, 0], [source_width, 0], [source_width, source_height], [0, source_height]],
                                 dtype=np.float32)
        matrix = cv2.getPerspectiveTransform(source_points, np.array(projected, dtype=np.float32))
        flag = cv2.INTER_LINEAR if get("smooth", True) == True else cv2.INTER_NEAREST
        warped = cv2.warpPerspective(np.ascontiguousarray(frame), matrix, (stage_width, stage_height), flags=flag,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        alpha = (warped[..., 3].astype(np.float32) / 255.0) * float(np.clip(get("opacity", 1.0), 0.0, 1.0))
        blend(canvas, warped[..., :3], alpha, str(get("blend_mode", "normal")))

    # --- regioni, maschere, edge blend, warp, route ---
    def render_region(self, stage_canvas: np.ndarray, region: dict) -> np.ndarray:
        x, y, width, height = [int(value) for value in region["bounds"]]
        output = stage_canvas[y:y + height, x:x + width].copy()
        blend_config = region.get("edge_blend", {})
        for edge, axis in (("left", "x"), ("right", "x"), ("top", "y"), ("bottom", "y")):
            size = int(blend_config.get(edge, 0))
            if size > 0:
                self._edge_blend(output, edge, size, float(blend_config.get("gamma", 2.2)))
        mask = region.get("mask")
        if mask is not None:
            if isinstance(mask, str):
                mask_image = cv2.imread(mask, cv2.IMREAD_GRAYSCALE)
            else:
                mask_image = np.asarray(mask, dtype=np.uint8)
            if mask_image is not None:
                mask_image = cv2.resize(mask_image, (output.shape[1], output.shape[0]))
                output[..., :3] = (output[..., :3].astype(np.float32) * (mask_image[..., None] / 255.0)).astype(np.uint8)
        warp = region.get("warp")
        if warp is not None and len(warp.get("corners", [])) == 4:
            source = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
            output = cv2.warpPerspective(output, cv2.getPerspectiveTransform(source, np.array(warp["corners"], dtype=np.float32)),
                                         (width, height))
        return output

    @staticmethod
    def _edge_blend(image: np.ndarray, edge: str, size: int, gamma: float) -> None:
        ramp = np.linspace(0.0, 1.0, size, dtype=np.float32) ** (1.0 / gamma)
        if edge == "left":
            image[:, :size, :3] = (image[:, :size, :3] * ramp[None, :, None]).astype(np.uint8)
        elif edge == "right":
            image[:, -size:, :3] = (image[:, -size:, :3] * ramp[::-1][None, :, None]).astype(np.uint8)
        elif edge == "top":
            image[:size, :, :3] = (image[:size, :, :3] * ramp[:, None, None]).astype(np.uint8)
        else:
            image[-size:, :, :3] = (image[-size:, :, :3] * ramp[::-1][:, None, None]).astype(np.uint8)

    def render_routes(self) -> dict[str, np.ndarray]:
        """Compone ogni stage una volta e invia ogni route al suo sink. Restituisce {route: frame}."""
        workspace = self.runtime.workspace
        stage_cache: dict[int, np.ndarray] = {}
        result = {}
        for route in workspace.patches["video_route"]:
            number = int(route.get("stage", 1))
            if number not in stage_cache:
                stage_cache[number] = self.render_stage(number)
            stage = self.stage_definition(number)
            region_name = route.get("region", "")
            region = next((item for item in stage.get("regions", []) if item.get("name") == region_name), None)
            if region is None:
                frame = stage_cache[number]
            else:
                frame = self.render_region(stage_cache[number], region)
            result[route["name"]] = frame
            self.sink.send(route["name"], frame)
        return result
