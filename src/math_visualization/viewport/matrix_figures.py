"""Matrices drawn as objects: their columns as arrows and the shape they span.

A 2×2 matrix is two arrows in the plane and the parallelogram they span
(signed area = det); a 3×3 matrix is three arrows and a parallelepiped
(signed volume = det). Operations are animated by moving the result's
columns with the parameter ``t`` ∈ [0, 1]; the operands stay as faint
references. Everything here is in mathematical (x, y, z) coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

from math_visualization.math_core.matrix_algebra import Matrix, OperationKind, identity, lerp, number
from math_visualization.scene.operation_record import OperationRecord

Point3 = tuple[float, float, float]
ORIGIN: Point3 = (0.0, 0.0, 0.0)


def columns3(matrix: Matrix) -> tuple[Point3, ...]:
    """The matrix's columns, with 2D columns embedded at z = 0."""
    return tuple((*column, 0.0) if len(column) == 2 else tuple(column) for column in matrix.columns)


@dataclass(frozen=True)
class FigureArrow:
    start: Point3
    end: Point3
    # Index of the column it stands for (0, 1, 2), which sets its colour.
    column: int
    # "result" is drawn solid, "operand" faint.
    role: str


@dataclass(frozen=True)
class Figure:
    """One matrix: the arrows of its columns from the origin and the shape they span."""

    columns: tuple[Point3, ...]
    role: str
    label: str = ""

    @property
    def arrows(self) -> tuple[FigureArrow, ...]:
        return tuple(FigureArrow(ORIGIN, column, index, self.role) for index, column in enumerate(self.columns))

    @property
    def corner(self) -> Point3:
        """The vertex opposite the origin (sum of the columns), where the label goes."""
        return tuple(sum(values) for values in zip(*self.columns))

    def polygon(self) -> list[Point3]:
        """The parallelogram of a 2×2 matrix: 0, c₁, c₁ + c₂, c₂."""
        first, second = self.columns[:2]
        return [ORIGIN, first, _add(first, second), second]

    def faces(self) -> list[list[Point3]]:
        """The six quadrilateral faces of a 3×3 matrix's parallelepiped."""
        a, b, c = self.columns
        o = ORIGIN
        ab, ac, bc, abc = _add(a, b), _add(a, c), _add(b, c), _add(_add(a, b), c)
        return [[o, a, ab, b], [c, ac, abc, bc], [o, a, ac, c], [b, ab, abc, bc], [o, b, bc, c], [a, ab, abc, ac]]

    def edges(self) -> list[tuple[Point3, Point3]]:
        if len(self.columns) == 2:
            points = self.polygon()
            return list(zip(points, points[1:] + points[:1]))
        unique = []
        for face in self.faces():
            for start, end in zip(face, face[1:] + face[:1]):
                if (end, start) not in unique and (start, end) not in unique:
                    unique.append((start, end))
        return unique


@dataclass(frozen=True)
class FigureScene:
    size: int
    figures: tuple[Figure, ...]
    # Arrows that are not a matrix's own columns (B's columns carried to A's tips).
    extra_arrows: tuple[FigureArrow, ...] = ()
    caption: str = ""

    @property
    def arrows(self) -> tuple[FigureArrow, ...]:
        return tuple(arrow for figure in self.figures for arrow in figure.arrows) + self.extra_arrows


def _add(p: Point3, q: Point3) -> Point3:
    return (p[0] + q[0], p[1] + q[1], p[2] + q[2])


def _scale(p: Point3, k: float) -> Point3:
    return (k * p[0], k * p[1], k * p[2])


def matrix_scene(matrix: Matrix, t: float, name: str) -> FigureScene:
    """The matrix growing out of the identity: I's unit square / cube becomes M's shape."""
    current = lerp(identity(matrix.size), matrix, t)
    unit = Figure(columns3(identity(matrix.size)), "operand")
    word = "area" if matrix.size == 2 else "volume"
    shape = Figure(columns3(current), "result", name)
    return FigureScene(
        matrix.size, (unit, shape), caption=f"det {name}(t) = {number(current.determinant)} (signed {word})"
    )


def operation_scene(record: OperationRecord, t: float) -> FigureScene:
    """The operation at parameter ``t``: the result's columns move from a start to their end."""
    kind = record.kind
    first = record.operands[0]
    size = first.size
    name = record.result_name or "C"
    a = columns3(first)
    if kind in (OperationKind.ADD, OperationKind.SUBTRACT):
        sign = 1.0 if kind is OperationKind.ADD else -1.0
        b = columns3(record.operands[1])
        result = tuple(_add(a_j, _scale(b_j, sign * t)) for a_j, b_j in zip(a, b))
        carried = tuple(
            FigureArrow(a_j, _add(a_j, _scale(b_j, sign)), index, "operand") for index, (a_j, b_j) in enumerate(zip(a, b))
        )
        operation = "+" if sign > 0 else "−"
        return FigureScene(
            size,
            (Figure(a, "operand", record.operand_names[0]), Figure(result, "result", name)),
            carried,
            f"each column: {name} column = {record.operand_names[0]} column {operation} {record.operand_names[1]} column",
        )
    if kind is OperationKind.SCALE:
        factor = 1.0 + t * (record.scalar - 1.0)
        result = tuple(_scale(a_j, factor) for a_j in a)
        return FigureScene(
            size,
            (Figure(a, "operand", record.operand_names[0]), Figure(result, "result", name)),
            caption=f"every column is stretched by k = {number(record.scalar)}",
        )
    if kind is OperationKind.MULTIPLY:
        second = record.operands[1]
        current = lerp(second, first @ second, t)
        return FigureScene(
            size,
            (Figure(columns3(second), "operand", record.operand_names[1]), Figure(columns3(current), "result", name)),
            caption=(
                f"each column of {record.operand_names[1]} is moved by {record.operand_names[0]}: "
                f"{name} column j = {record.operand_names[0]} · ({record.operand_names[1]} column j)"
            ),
        )
    if kind is OperationKind.TRANSPOSE:
        current = lerp(first, first.transpose(), t)
        return FigureScene(
            size,
            (Figure(a, "operand", record.operand_names[0]), Figure(columns3(current), "result", name)),
            caption=f"the rows of {record.operand_names[0]} become the columns of {name}",
        )
    # Determinant: the unit square / cube is carried to the operand's shape.
    return matrix_scene(first, t, record.operand_names[0])
