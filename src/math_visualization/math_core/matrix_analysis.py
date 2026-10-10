"""What a 2×2 matrix does to the plane: area, orientation, rank and invertibility.

Every property is derived from one :class:`MatrixAnalysis` so they all use the
same tolerance policy (:mod:`tolerances`) and can never contradict each other:
a matrix is invertible exactly when its rank is 2, its orientation is
"collapsed" exactly when its rank is below 2, and so on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.math_core.matrix3 import Matrix3
from math_visualization.math_core.tolerances import NEAR_SINGULAR_RATIO
from math_visualization.math_core.vector2 import Vector2


class Orientation(Enum):
    PRESERVED = "preserved"
    REVERSED = "reversed"
    # Rank below full: the space is squashed onto a plane, a line or a point.
    COLLAPSED = "collapsed"


class MatrixStatus(Enum):
    REGULAR = "regular"
    NEAR_SINGULAR = "near_singular"
    SINGULAR = "singular"


@dataclass(frozen=True)
class MatrixAnalysis:
    matrix: Matrix2 | Matrix3
    determinant: float
    rank: int
    singular_values: tuple[float, float]

    @property
    def area_scale(self) -> float:
        """Factor by which every area is multiplied: |det A|."""
        return abs(self.determinant)

    @property
    def size(self) -> int:
        return self.matrix.size

    @property
    def is_invertible(self) -> bool:
        return self.rank == self.size

    @property
    def orientation(self) -> Orientation:
        if not self.is_invertible:
            return Orientation.COLLAPSED
        return Orientation.PRESERVED if self.determinant > 0.0 else Orientation.REVERSED

    @property
    def condition_number(self) -> float:
        """κ = σ_max / σ_min; infinite for a singular matrix."""
        largest, smallest = self.singular_values
        return largest / smallest if self.is_invertible else math.inf

    @property
    def status(self) -> MatrixStatus:
        if not self.is_invertible:
            return MatrixStatus.SINGULAR
        largest, smallest = self.singular_values
        if smallest < NEAR_SINGULAR_RATIO * largest:
            return MatrixStatus.NEAR_SINGULAR
        return MatrixStatus.REGULAR

    @property
    def inverse(self) -> Matrix2 | Matrix3 | None:
        return self.matrix.inverse() if self.is_invertible else None

    @property
    def image_direction(self) -> Vector2 | None:
        """Unit direction of the line the plane collapses onto (2×2 of rank 1 only).

        The longer column spans the image; using it avoids normalising a
        column that is (numerically) zero.
        """
        if self.size != 2 or self.rank != 1:
            return None
        first, second = self.matrix.first_column, self.matrix.second_column
        column = first if first.length >= second.length else second
        return column * (1.0 / column.length)

    @property
    def kernel_direction(self) -> Vector2 | None:
        """Unit direction of the null space: the inputs sent to the origin (rank 1 only).

        The kernel is perpendicular to the row space, which the longer row spans.
        """
        if self.size != 2 or self.rank != 1:
            return None
        (a, b), (c, d) = self.matrix.rows
        x, y = (a, b) if math.hypot(a, b) >= math.hypot(c, d) else (c, d)
        length = math.hypot(x, y)
        return Vector2(-y / length, x / length)


def analyze(matrix: Matrix2 | Matrix3) -> MatrixAnalysis:
    return MatrixAnalysis(
        matrix=matrix,
        determinant=matrix.determinant,
        rank=matrix.rank(),
        singular_values=matrix.singular_values,
    )
