"""The single numerical tolerance policy shared by the mathematical core.

Floating-point results are never compared with ``==`` to decide mathematical
properties such as "this vector is zero". Rank, invertibility and the
singular / near-singular status of a matrix all read the same two thresholds
below, so they can never disagree with one another.
"""

from __future__ import annotations

ABSOLUTE_TOLERANCE = 1e-9
# A matrix is singular when σ_min ≤ SINGULAR_RATIO · σ_max. The ratio does not
# change when the matrix is scaled, so 1e-6·I stays invertible.
SINGULAR_RATIO = 1e-9
# Invertible, but σ_min / σ_max below this squashes the plane so much that it
# is visually indistinguishable from a line: flagged as near-singular.
NEAR_SINGULAR_RATIO = 1e-3


def is_zero(value: float, tolerance: float = ABSOLUTE_TOLERANCE) -> bool:
    """Return whether ``value`` is zero within ``tolerance``."""
    return abs(value) <= tolerance
