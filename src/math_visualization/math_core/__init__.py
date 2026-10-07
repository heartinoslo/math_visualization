"""Qt-free mathematical core: value types and numerical tolerance policy."""

from math_visualization.math_core.tolerances import ABSOLUTE_TOLERANCE, is_zero
from math_visualization.math_core.vector2 import Vector2

__all__ = ["ABSOLUTE_TOLERANCE", "Vector2", "is_zero"]
