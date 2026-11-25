"""Conversioni di tempo e di livelli in dB usate da tutta la sezione Cue."""
from __future__ import annotations

import math

MINUS_INFINITY = -math.inf


def parse_time(text) -> float:
    """Accetta 's', 'm:s', 'h:m:s' con decimali; numeri passano invariati. Stringa vuota = 0."""
    if isinstance(text, (int, float)):
        return float(text)
    cleaned = str(text).strip().replace(",", ".")
    if cleaned == "":
        return 0.0
    parts = cleaned.split(":")
    if len(parts) > 3:
        raise ValueError("tempo non valido: " + str(text))
    total = 0.0
    for part in parts:
        if part.strip() == "":
            part = "0"
        total = total * 60.0 + float(part)
    return total


def format_time(seconds: float, decimals: int = 2) -> str:
    """Formato h:mm:ss.xx (le ore compaiono solo se servono)."""
    if seconds is None:
        return ""
    negative = seconds < 0
    seconds = abs(seconds)
    whole = int(seconds)
    fraction = seconds - whole
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    fraction_text = ("%." + str(decimals) + "f") % fraction
    if fraction_text.startswith("1"):
        secs = secs + 1
        fraction_text = ("%." + str(decimals) + "f") % 0.0
    fraction_text = fraction_text[1:]
    if decimals == 0:
        fraction_text = ""
    if hours > 0:
        text = "%d:%02d:%02d%s" % (hours, minutes, secs, fraction_text)
    else:
        text = "%d:%02d%s" % (minutes, secs, fraction_text)
    if negative == True:
        text = "-" + text
    return text


def parse_db(text, negative_by_default: bool = True) -> float:
    """Numero senza segno = negativo (regola QLab). '+' per positivo. Vuoto = -inf."""
    if isinstance(text, (int, float)):
        return float(text)
    cleaned = str(text).strip().lower().replace(",", ".")
    if cleaned in ("", "-inf", "inf", "-infinity"):
        return MINUS_INFINITY
    if cleaned.startswith("+"):
        return abs(float(cleaned[1:]))
    value = float(cleaned)
    if cleaned.startswith("-") == False and negative_by_default == True:
        return -abs(value)
    return value


def format_db(value: float) -> str:
    if value is None or value == MINUS_INFINITY or value <= -180.0:
        return "-INF"
    return ("%+.1f" % value) if value > 0 else ("%.1f" % value)


def db_to_linear(value: float) -> float:
    if value == MINUS_INFINITY or value is None:
        return 0.0
    return math.pow(10.0, value / 20.0)


def linear_to_db(value: float) -> float:
    if value <= 0.0:
        return MINUS_INFINITY
    return 20.0 * math.log10(value)


def clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value
