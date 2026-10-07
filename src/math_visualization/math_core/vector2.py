"""Immutable two-dimensional real vector."""

from __future__ import annotations

import math
from dataclasses import dataclass

from math_visualization.math_core.tolerances import ABSOLUTE_TOLERANCE, is_zero


@dataclass(frozen=True)
class Vector2:
    """A vector in R² with finite components."""

    x: float
    y: float

    def __post_init__(self) -> None:
        for name in ("x", "y"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number, got {value!r}")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
            # Store plain floats and fold -0.0 into 0.0 for stable display and equality.
            object.__setattr__(self, name, float(value) + 0.0)

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def angle_degrees(self) -> float:
        """Direction angle from +x, counter-clockwise, in ``(-180, 180]``; 0 for the zero vector."""
        if self.is_zero():
            return 0.0
        angle = math.degrees(math.atan2(self.y, self.x))
        return 180.0 if angle == -180.0 else angle

    def is_zero(self, tolerance: float = ABSOLUTE_TOLERANCE) -> bool:
        return is_zero(self.length, tolerance)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def __add__(self, other: Vector2) -> Vector2:
        if not isinstance(other, Vector2):
            return NotImplemented
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        if not isinstance(other, Vector2):
            return NotImplemented
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        if isinstance(scalar, bool) or not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)
