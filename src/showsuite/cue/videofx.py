"""Effetti video dei cue Video/Camera/Text (manuale QLab 5.7 e Parameter Reference).

Ogni effetto ha un nome di scripting (quello del manuale) e parametri con i nomi di scripting del manuale. QLab li
implementa con i filtri Core Image di macOS: qui sono riscritti con numpy/OpenCV, quindi il risultato è SIMILE ma
non identico pixel per pixel. Sono implementati SOLO gli effetti elencati in `EFFECTS`; gli altri del manuale
(distorsioni, tile, kaleidoscope, droste, spotlight, ecc.) NON sono disponibili e `add` li rifiuta.
Gli effetti sono applicati in ordine sul frame RGBA (uint8) prima della geometria del layer."""
from __future__ import annotations

import math

import cv2
import numpy as np

IDENTITY_MATRIX = {"R_R": 1.0, "G_R": 0.0, "B_R": 0.0, "A_R": 0.0, "R_Bias": 0.0,
                   "R_G": 0.0, "G_G": 1.0, "B_G": 0.0, "A_G": 0.0, "G_Bias": 0.0,
                   "R_B": 0.0, "G_B": 0.0, "B_B": 1.0, "A_B": 0.0, "B_Bias": 0.0,
                   "R_A": 0.0, "G_A": 0.0, "B_A": 0.0, "A_A": 1.0, "A_Bias": 0.0}


def _rgb_float(frame: np.ndarray) -> np.ndarray:
    return frame[..., :3].astype(np.float32) / 255.0


def _store(frame: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    result = frame.copy()
    result[..., :3] = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return result


def _color_controls(frame, parameters):
    rgb = _rgb_float(frame)
    saturation = float(parameters["inputSaturation"])
    luminance = (rgb[..., 0:1] * 0.299 + rgb[..., 1:2] * 0.587 + rgb[..., 2:3] * 0.114)
    rgb = luminance + (rgb - luminance) * saturation
    rgb = (rgb - 0.5) * float(parameters["inputContrast"]) + 0.5 + float(parameters["inputBrightness"])
    angle = float(parameters["inputAngle"])
    if angle != 0.0:
        hsv = cv2.cvtColor(np.clip(rgb, 0.0, 1.0), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = (hsv[..., 0] + angle) % 360.0
        rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return _store(frame, np.clip(rgb, 0.0, 1.0))


def _exposure(frame, parameters):
    return _store(frame, np.clip(_rgb_float(frame) * (2.0 ** float(parameters["inputEV"])), 0.0, 1.0))


def _gamma(frame, parameters):
    return _store(frame, np.power(np.clip(_rgb_float(frame), 0.0, 1.0), max(0.0, float(parameters["inputPower"]))))


def _sepia_monochrome(frame, parameters):
    rgb = _rgb_float(frame)
    luminance = (rgb[..., 0:1] * 0.299 + rgb[..., 1:2] * 0.587 + rgb[..., 2:3] * 0.114)
    if int(parameters["Choose_Effect"]) == 0:
        matrix = np.array([[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]], dtype=np.float32)
        toned = np.clip(rgb @ matrix.T, 0.0, 1.0)
    else:
        color = np.array(parameters["inputColor"][:3], dtype=np.float32)
        toned = np.clip(luminance * color * 2.0, 0.0, 1.0)
    intensity = float(parameters["inputIntensity"])
    return _store(frame, rgb + (toned - rgb) * intensity)


def _min_max_invert(frame, parameters):
    rgb = _rgb_float(frame)
    mode = int(parameters["Choose_Effect"])
    if mode == 0:
        result = np.repeat(rgb.min(axis=2, keepdims=True), 3, axis=2)
    elif mode == 1:
        result = np.repeat(rgb.max(axis=2, keepdims=True), 3, axis=2)
    else:
        result = 1.0 - rgb
    return _store(frame, result)


def _vibrance(frame, parameters):
    rgb = _rgb_float(frame)
    amount = float(parameters["inputAmount"])
    luminance = (rgb[..., 0:1] * 0.299 + rgb[..., 1:2] * 0.587 + rgb[..., 2:3] * 0.114)
    current = rgb.max(axis=2, keepdims=True) - rgb.min(axis=2, keepdims=True)
    boost = 1.0 + amount * (1.0 - current)
    return _store(frame, np.clip(luminance + (rgb - luminance) * boost, 0.0, 1.0))


def _color_clamp(frame, parameters):
    result = frame.copy()
    for index, channel in enumerate("RGBA"):
        low = float(parameters["Min_" + channel]) * 255.0
        high = float(parameters["Max_" + channel]) * 255.0
        result[..., index] = np.clip(frame[..., index].astype(np.float32), low, max(low, high)).astype(np.uint8)
    return result


def _color_matrix(frame, parameters):
    pixels = frame.astype(np.float32) / 255.0
    result = np.zeros_like(pixels)
    for row, channel in enumerate("RGBA"):
        total = float(parameters[channel + "_Bias"])
        for column, source in enumerate("RGBA"):
            total = total + pixels[..., column] * float(parameters[source + "_" + channel])
        result[..., row] = total
    return np.clip(result * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _color_threshold(frame, parameters):
    luminance = (_rgb_float(frame) @ np.array([0.299, 0.587, 0.114], dtype=np.float32))
    mask = (luminance >= float(parameters["inputThreshold"])).astype(np.float32)[..., None]
    return _store(frame, np.repeat(mask, 3, axis=2))


def _posterize(frame, parameters):
    levels = max(2.0, float(parameters["inputLevels"]))
    return _store(frame, np.floor(_rgb_float(frame) * levels) / (levels - 1.0) if levels > 1.0 else _rgb_float(frame))


def _blur(frame, parameters):
    radius = float(parameters["inputRadius"])
    if radius <= 0.0:
        return frame
    mode = int(parameters["Choose_Blur"])
    size = int(radius) * 2 + 1
    if mode == 0:
        return cv2.blur(frame, (size, size))
    if mode == 1:
        kernel = np.zeros((size, size), dtype=np.float32)
        cv2.circle(kernel, (size // 2, size // 2), max(1, int(radius)), 1.0, -1)
        return cv2.filter2D(frame, -1, kernel / kernel.sum())
    return cv2.GaussianBlur(frame, (0, 0), radius)


def _motion_blur(frame, parameters):
    radius = int(float(parameters["inputRadius"]))
    if radius <= 0:
        return frame
    size = radius * 2 + 1
    kernel = np.zeros((size, size), dtype=np.float32)
    angle = math.radians(float(parameters["inputAngle"]))
    cv2.line(kernel, (int(radius - math.cos(angle) * radius), int(radius + math.sin(angle) * radius)),
             (int(radius + math.cos(angle) * radius), int(radius - math.sin(angle) * radius)), 1.0, 1)
    return cv2.filter2D(frame, -1, kernel / kernel.sum())


def _unsharp(frame, radius: float, intensity: float):
    blurred = cv2.GaussianBlur(frame, (0, 0), max(0.1, radius))
    result = frame.copy()
    result[..., :3] = cv2.addWeighted(frame[..., :3], 1.0 + intensity, blurred[..., :3], -intensity, 0)
    return result


def _sharpen(frame, parameters):
    return _unsharp(frame, 1.0, float(parameters["inputSharpness"]))


def _unsharp_mask(frame, parameters):
    return _unsharp(frame, float(parameters["inputRadius"]), float(parameters["inputIntensity"]))


def _pixellate(frame, parameters):
    # La variante esagonale (Choose_Effect 1) è approssimata con blocchi quadrati.
    scale = max(1, int(float(parameters["inputScale"])))
    height, width = frame.shape[:2]
    small = cv2.resize(frame, (max(1, width // scale), max(1, height // scale)), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)


def _mask_alpha(frame, mask: np.ndarray):
    result = frame.copy()
    result[..., 3] = (frame[..., 3].astype(np.float32) * mask).astype(np.uint8)
    return result


def _shutter(frame, parameters):
    height, width = frame.shape[:2]
    left, right = float(parameters["Left"]) * width, float(parameters["Right"]) * width
    bottom, top = float(parameters["Bottom"]) * height, float(parameters["Top"]) * height
    mask = np.zeros((height, width), dtype=np.float32)
    if int(parameters["Shape"]) == 1:
        center = (int((left + right) / 2.0), int(height - (bottom + top) / 2.0))
        axes = (max(1, int(abs(right - left) / 2.0)), max(1, int(abs(top - bottom) / 2.0)))
        cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)
    else:
        mask[int(height - max(bottom, top)):int(height - min(bottom, top)), int(min(left, right)):int(max(left, right))] = 1.0
    feather = float(parameters["Feather"])
    if feather > 0.0:
        mask = cv2.GaussianBlur(mask, (0, 0), feather / 2.0)
    return _mask_alpha(frame, mask)


def _window(frame, parameters):
    height, width = frame.shape[:2]
    mask = np.zeros((height, width), dtype=np.float32)
    start_x = float(parameters["Origin_X"]) * width
    start_y = float(parameters["Origin_Y"]) * height
    end_x = start_x + float(parameters["Size_W"]) * width
    end_y = start_y + float(parameters["Size_H"]) * height
    mask[int(height - end_y):int(height - start_y), int(start_x):int(end_x)] = 1.0
    return _mask_alpha(frame, mask)


EFFECTS = {
    "ColorControls": {"title": "Color Controls", "apply": _color_controls,
                      "parameters": {"inputBrightness": 0.0, "inputContrast": 1.0, "inputAngle": 0.0, "inputSaturation": 1.0}},
    "Exposure": {"title": "Exposure", "apply": _exposure, "parameters": {"inputEV": 0.0}},
    "Gamma": {"title": "Gamma", "apply": _gamma, "parameters": {"inputPower": 1.0}},
    "SepiaMonochrome": {"title": "Sepia / Monochrome", "apply": _sepia_monochrome,
                        "parameters": {"Choose_Effect": 0, "inputColor": [0.6, 0.45, 0.3, 1.0], "inputIntensity": 1.0}},
    "MinMaxInvert": {"title": "Min / Max / Invert", "apply": _min_max_invert, "parameters": {"Choose_Effect": 2}},
    "Vibrance": {"title": "Vibrance", "apply": _vibrance, "parameters": {"inputAmount": 0.0}},
    "ColorClamp": {"title": "Color Clamp", "apply": _color_clamp,
                   "parameters": {"Min_R": 0.0, "Max_R": 1.0, "Min_G": 0.0, "Max_G": 1.0, "Min_B": 0.0, "Max_B": 1.0,
                                  "Min_A": 0.0, "Max_A": 1.0}},
    "ColorMatrix": {"title": "Color Matrix", "apply": _color_matrix, "parameters": dict(IDENTITY_MATRIX)},
    "ColorThreshold": {"title": "Color Threshold", "apply": _color_threshold, "parameters": {"inputThreshold": 0.5}},
    "ColorPosterize": {"title": "Color Posterize", "apply": _posterize, "parameters": {"inputLevels": 6.0}},
    "BoxDiscGaussianBlur": {"title": "Box / Disc / Gaussian Blur", "apply": _blur,
                            "parameters": {"Choose_Blur": 2, "inputRadius": 10.0}},
    "MotionBlur": {"title": "Motion Blur", "apply": _motion_blur, "parameters": {"inputRadius": 20.0, "inputAngle": 0.0}},
    "SharpenLuminance": {"title": "Sharpen Luminance", "apply": _sharpen, "parameters": {"inputSharpness": 0.4}},
    "UnsharpMask": {"title": "Unsharp Mask", "apply": _unsharp_mask, "parameters": {"inputRadius": 2.5, "inputIntensity": 0.5}},
    "Pixellation": {"title": "Pixellation", "apply": _pixellate,
                    "parameters": {"Choose_Effect": 0, "_protocolInput_X": 0.5, "_protocolInput_Y": 0.5, "inputScale": 8.0}},
    "Shutter": {"title": "Shutter", "apply": _shutter,
                "parameters": {"Shape": 0, "Left": 0.0, "Right": 1.0, "Bottom": 0.0, "Top": 1.0, "Feather": 0.0}},
    "Window": {"title": "Window", "apply": _window,
               "parameters": {"Origin_X": 0.0, "Origin_Y": 0.0, "Size_W": 1.0, "Size_H": 1.0}},
}


def new_effect(name: str) -> dict:
    if name not in EFFECTS:
        raise ValueError("effetto video non disponibile: " + name)
    return {"name": name, "enabled": True, "parameters": {key: (list(value) if isinstance(value, list) else value)
                                                          for key, value in EFFECTS[name]["parameters"].items()}}


def set_parameter(effect: dict, key: str, value) -> None:
    if key not in EFFECTS[effect["name"]]["parameters"]:
        raise ValueError("parametro sconosciuto: " + key)
    default = EFFECTS[effect["name"]]["parameters"][key]
    if isinstance(default, list):
        effect["parameters"][key] = [float(item) for item in value]
    elif isinstance(default, int):
        effect["parameters"][key] = int(value)
    else:
        effect["parameters"][key] = float(value)


def apply_effects(frame: np.ndarray, effects: list) -> np.ndarray:
    """Applica in ordine gli effetti abilitati a un frame RGBA uint8; effetti sconosciuti vengono ignorati."""
    for effect in effects:
        if effect.get("enabled", True) == False or effect.get("name") not in EFFECTS:
            continue
        parameters = dict(EFFECTS[effect["name"]]["parameters"])
        parameters.update(effect.get("parameters", {}))
        frame = EFFECTS[effect["name"]]["apply"](np.ascontiguousarray(frame), parameters)
    return frame
