"""Pure geometry of a linearly transformed plane: grid lines, unit square, clipping."""

from __future__ import annotations

import math

from math_visualization.math_core.matrix2 import Matrix2


Point = tuple[float, float]
Segment = tuple[Point, Point]

# Upper bound on transformed grid lines per direction and side of the origin.
MAX_LINES_PER_SIDE = 40


def smallest_singular_value(matrix: Matrix2) -> float:
    """σ_min of a 2×2 matrix (see :attr:`Matrix2.singular_values`)."""
    return matrix.singular_values[1]


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


def orientation_arc(
    matrix: Matrix2, radius: float, head_length: float, head_half_width: float, segments: int = 32
) -> tuple[list[Point], list[Point]] | None:
    """Arc from A·e₁ to A·e₂ around the origin, with an arrowhead at A·e₂.

    It sweeps the signed angle from the first column to the second, whose sine
    has the sign of det A: counter-clockwise when orientation is preserved,
    clockwise when it is reversed. Returns ``(arc_points, head_triangle)``, or
    ``None`` when the columns are not independent (no orientation).
    """
    if matrix.rank() < 2 or radius <= 0.0:
        return None
    first, second = matrix.first_column, matrix.second_column
    start = math.atan2(first.y, first.x)
    sweep = math.atan2(matrix.determinant, first.dot(second))
    # Keep the head inside the arc: at most half of its length.
    head = min(head_length, 0.5 * radius * abs(sweep))
    end = start + sweep
    shaft_end = end - math.copysign(head / radius, sweep)
    arc = [
        (radius * math.cos(angle), radius * math.sin(angle))
        for angle in (start + (shaft_end - start) * k / segments for k in range(segments + 1))
    ]
    tip = (radius * math.cos(end), radius * math.sin(end))
    base_x, base_y = radius * math.cos(shaft_end), radius * math.sin(shaft_end)
    # Head base perpendicular to the arc: along the radial direction.
    radial_x, radial_y = math.cos(shaft_end), math.sin(shaft_end)
    width = head_half_width * head / head_length if head_length > 0.0 else 0.0
    head_triangle = [
        tip,
        (base_x + width * radial_x, base_y + width * radial_y),
        (base_x - width * radial_x, base_y - width * radial_y),
    ]
    return arc, head_triangle


def line_through_origin(direction: tuple[float, float], half_length: float) -> Segment:
    """The segment of the line ``span{direction}`` within ``half_length`` of the origin."""
    x, y = direction
    return ((-half_length * x, -half_length * y), (half_length * x, half_length * y))


def ribbon(points: list[Point], half_width: float) -> list[Point]:
    """Triangles (three points each) of a flat strip of ``2·half_width`` along a polyline."""
    triangles: list[Point] = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0.0:
            continue
        nx, ny = -(y2 - y1) / length * half_width, (x2 - x1) / length * half_width
        a, b = (x1 + nx, y1 + ny), (x1 - nx, y1 - ny)
        c, d = (x2 + nx, y2 + ny), (x2 - nx, y2 - ny)
        triangles.extend((a, b, c, c, b, d))
    return triangles
