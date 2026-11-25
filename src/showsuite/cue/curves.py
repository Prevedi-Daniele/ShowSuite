"""Curve di fade condivise da Fade cue, Light cue e Network cue (fade 1D/2D).

Le formule di S-curve e parametrica sono approssimazioni: il manuale non le specifica (SPEC-audio-video-light §D.2)."""
from __future__ import annotations

import math

CURVE_TYPES = ("s_curve", "linear", "custom", "parametric")


def linear(position: float) -> float:
    return position


def s_curve(position: float) -> float:
    """Ease-in/ease-out (smootherstep)."""
    return position * position * position * (position * (position * 6.0 - 15.0) + 10.0)


def parametric(position: float, intensity: float) -> float:
    """intensity 0 = lineare; 1 = equal power (seno quarto d'onda); valori intermedi per miscela."""
    equal_power = math.sin(position * math.pi / 2.0)
    return (1.0 - intensity) * position + intensity * equal_power


def custom(position: float, points: list) -> float:
    """Interpolazione lineare tra punti (x, y) ordinati con x in 0..1."""
    if len(points) == 0:
        return position
    ordered = sorted(points, key=lambda point: point[0])
    if position <= ordered[0][0]:
        return ordered[0][1]
    for index in range(1, len(ordered)):
        left = ordered[index - 1]
        right = ordered[index]
        if position <= right[0]:
            span = right[0] - left[0]
            if span <= 0:
                return right[1]
            return left[1] + (right[1] - left[1]) * (position - left[0]) / span
    return ordered[-1][1]


def default_curve() -> dict:
    return {"type": "s_curve", "intensity": 0.5, "rising": [[0.0, 0.0], [1.0, 1.0]], "falling": [[0.0, 0.0], [1.0, 1.0]]}


def evaluate(curve: dict | None, position: float, rising: bool = True) -> float:
    """Valore 0..1 della curva alla posizione 0..1. Rising/falling scelgono il ramo per le curve custom."""
    if position <= 0.0:
        return 0.0
    if position >= 1.0:
        return 1.0
    if curve is None:
        return s_curve(position)
    kind = curve.get("type", "s_curve")
    if kind == "linear":
        return linear(position)
    if kind == "parametric":
        return parametric(position, float(curve.get("intensity", 0.5)))
    if kind == "custom":
        branch = "rising" if rising == True else "falling"
        return custom(position, curve.get(branch, [[0.0, 0.0], [1.0, 1.0]]))
    return s_curve(position)


def interpolate(start: float, end: float, position: float, curve: dict | None) -> float:
    shaped = evaluate(curve, position, end >= start)
    return start + (end - start) * shaped


def slerp(first: list, second: list, position: float) -> list:
    """Interpolazione sferica tra quaternioni (usata per la rotazione 3D dei Fade video)."""
    dot = sum(a * b for a, b in zip(first, second))
    other = list(second)
    if dot < 0.0:
        other = [-value for value in other]
        dot = -dot
    if dot > 0.9995:
        mixed = [a + position * (b - a) for a, b in zip(first, other)]
    else:
        theta = math.acos(dot)
        sin_theta = math.sin(theta)
        weight_first = math.sin((1.0 - position) * theta) / sin_theta
        weight_second = math.sin(position * theta) / sin_theta
        mixed = [weight_first * a + weight_second * b for a, b in zip(first, other)]
    length = math.sqrt(sum(value * value for value in mixed))
    if length == 0.0:
        return list(first)
    return [value / length for value in mixed]
