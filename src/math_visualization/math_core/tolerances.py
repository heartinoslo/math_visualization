"""The single numerical tolerance policy shared by the mathematical core.

Floating-point results are never compared with ``==`` to decide mathematical
properties such as "this vector is zero". Later stages (rank, invertibility)
must use the same helpers so every property agrees on the same threshold.
"""

from __future__ import annotations

ABSOLUTE_TOLERANCE = 1e-9


def is_zero(value: float, tolerance: float = ABSOLUTE_TOLERANCE) -> bool:
    """Return whether ``value`` is zero within ``tolerance``."""
    return abs(value) <= tolerance
