"""Pure geometry of a linearly transformed plane: grid lines, unit square, clipping."""

from __future__ import annotations

import math

from math_visualization.math_core.matrix2 import Matrix2


Point = tuple[float, float]
Segment = tuple[Point, Point]

# Upper bound on transformed grid lines per direction and side of the origin.
MAX_LINES_PER_SIDE = 40


def smallest_singular_value(matrix: Matrix2) -> float:
    """σ_min of a 2×2 matrix, computed without catastrophic cancellation.

    σ_max² = (‖A‖² + √D) / 2 with D = ‖A‖⁴ − 4·det². D is evaluated as the
    product ((a−d)² + (b+c)²)·((a+d)² + (b−c)²), which equals it exactly but
    never subtracts nearly equal numbers; σ_min then follows as |det| / σ_max.
    """
    a, b, c, d = matrix.entries
    frobenius_squared = a * a + b * b + c * c + d * d
    discriminant = ((a - d) ** 2 + (b + c) ** 2) * ((a + d) ** 2 + (b - c) ** 2)
    largest = math.sqrt((frobenius_squared + math.sqrt(discriminant)) / 2.0)
    return 0.0 if largest == 0.0 else abs(matrix.determinant) / largest


def lines_per_side(matrix: Matrix2, radius: float, step: float) -> int:
    """How many grid lines on each side of the origin cover a disc of ``radius``.

    A lattice point ``p`` lands within ``radius`` only if ``|p| <= radius / σ_min``.
    A (near-)singular matrix squashes the whole plane, so the count is capped.
    """
    sigma = smallest_singular_value(matrix)
    if sigma * step <= 0.0:
        return MAX_LINES_PER_SIDE
    return min(MAX_LINES_PER_SIDE, math.ceil(radius / (sigma * step)) + 1)


def transformed_grid(matrix: Matrix2, step: float, count: int) -> tuple[list[Segment], list[Segment]]:
    """Images of the lines ``x = k·step`` and ``y = k·step`` for ``|k| <= count``.

    Returns ``(grid_lines, axis_lines)``; the two lines through the origin are
    the transformed axes. Lines collapsed to a point are dropped.
    """
    extent = count * step
    lines: list[Segment] = []
    axes: list[Segment] = []
    for k in range(-count, count + 1):
        offset = k * step
        for start, end in (((offset, -extent), (offset, extent)), ((-extent, offset), (extent, offset))):
            image = (matrix.apply_point(*start), matrix.apply_point(*end))
            if math.dist(*image) <= 1e-12:
                continue
            (axes if k == 0 else lines).append(image)
    return lines, axes


def unit_square(matrix: Matrix2) -> list[Point]:
    """Images of (0, 0), (1, 0), (1, 1), (0, 1) — a parallelogram spanned by the columns."""
    return [matrix.apply_point(x, y) for x, y in ((0, 0), (1, 0), (1, 1), (0, 1))]


def clip_segment(segment: Segment, left: float, top: float, right: float, bottom: float) -> Segment | None:
    """Liang–Barsky clip of a segment to an axis-aligned rectangle, or ``None`` if outside."""
    (x1, y1), (x2, y2) = segment
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - left), (dx, right - x1), (-dy, y1 - top), (dy, bottom - y1)):
        if p == 0.0:
            if q < 0.0:
                return None
            continue
        ratio = q / p
        if p < 0.0:
            if ratio > t1:
                return None
            t0 = max(t0, ratio)
        else:
            if ratio < t0:
                return None
            t1 = min(t1, ratio)
    return ((x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy))
