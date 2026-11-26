"""Geometria pura (senza numpy) usata da API e video."""
from __future__ import annotations

import math


def euler_to_quaternion(x_degrees: float, y_degrees: float, z_degrees: float) -> list[float]:
    cx, sx = math.cos(math.radians(x_degrees) / 2), math.sin(math.radians(x_degrees) / 2)
    cy, sy = math.cos(math.radians(y_degrees) / 2), math.sin(math.radians(y_degrees) / 2)
    cz, sz = math.cos(math.radians(z_degrees) / 2), math.sin(math.radians(z_degrees) / 2)
    return [cx * cy * cz + sx * sy * sz, sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz]
