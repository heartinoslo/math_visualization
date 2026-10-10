"""Immutable real 3×3 matrix.

It mirrors :class:`Matrix2`: row-major entries, columns are the images of the
standard basis, and rank uses the same scale-invariant σ_min / σ_max test.
Points are plain ``(x, y, z)`` tuples.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from math_visualization.math_core.tolerances import ABSOLUTE_TOLERANCE, SINGULAR_RATIO

Point3 = tuple[float, float, float]


@dataclass(frozen=True)
class Matrix3:
    """The matrix with rows ``values[0:3]``, ``values[3:6]``, ``values[6:9]``."""

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        values = tuple(self.values)
        if len(values) != 9:
            raise ValueError(f"a 3×3 matrix needs 9 entries, got {len(values)}")
        cleaned = []
        for index, value in enumerate(values):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"entry {index} must be a real number, got {value!r}")
            if not math.isfinite(value):
                raise ValueError(f"entry {index} must be a finite number, got {value!r}")
            cleaned.append(float(value) + 0.0)
        object.__setattr__(self, "values", tuple(cleaned))

    @classmethod
    def identity(cls) -> Matrix3:
        return cls((1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))

    @classmethod
    def from_rows(cls, rows) -> Matrix3:
        return cls(tuple(value for row in rows for value in row))

    @classmethod
    def from_columns(cls, columns) -> Matrix3:
        return cls.from_rows(zip(*columns))

    @property
    def size(self) -> int:
        return 3

    @property
    def entries(self) -> tuple[float, ...]:
        """Row-major entries."""
        return self.values

    @property
    def rows(self) -> tuple[tuple[float, float, float], ...]:
        v = self.values
        return (v[0:3], v[3:6], v[6:9])

    @property
    def columns(self) -> tuple[Point3, Point3, Point3]:
        return tuple(zip(*self.rows))

    def entry(self, row: int, column: int) -> float:
        return self.values[3 * row + column]

    @property
    def determinant(self) -> float:
        a, b, c, d, e, f, g, h, i = self.values
        return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)

    @property
    def frobenius_norm(self) -> float:
        return math.sqrt(sum(value * value for value in self.values))

    @property
    def singular_values(self) -> tuple[float, float]:
        """``(σ_max, σ_min)``."""
        sigma = np.linalg.svd(np.array(self.rows), compute_uv=False)
        return (float(sigma[0]), float(sigma[-1]))

    def rank(self, tolerance: float = ABSOLUTE_TOLERANCE, ratio: float = SINGULAR_RATIO) -> int:
        """Number of singular values above ``ratio · σ_max`` (0 for the zero matrix)."""
        sigma = np.linalg.svd(np.array(self.rows), compute_uv=False)
        if sigma[0] <= tolerance:
            return 0
        return int(sum(1 for value in sigma if value > ratio * sigma[0]))

    def is_invertible(self) -> bool:
        return self.rank() == 3

    def inverse(self) -> Matrix3:
        if not self.is_invertible():
            raise ValueError("A singular matrix has no inverse")
        return Matrix3.from_rows(np.linalg.inv(np.array(self.rows)).tolist())

    def transpose(self) -> Matrix3:
        return Matrix3.from_rows(self.columns)

    def apply_point(self, x: float, y: float, z: float) -> Point3:
        r0, r1, r2 = self.rows
        return (
            r0[0] * x + r0[1] * y + r0[2] * z,
            r1[0] * x + r1[1] * y + r1[2] * z,
            r2[0] * x + r2[1] * y + r2[2] * z,
        )

    def __add__(self, other: Matrix3) -> Matrix3:
        if not isinstance(other, Matrix3):
            return NotImplemented
        return Matrix3(tuple(x + y for x, y in zip(self.values, other.values)))

    def __sub__(self, other: Matrix3) -> Matrix3:
        if not isinstance(other, Matrix3):
            return NotImplemented
        return Matrix3(tuple(x - y for x, y in zip(self.values, other.values)))

    def scaled(self, factor: float) -> Matrix3:
        return Matrix3(tuple(factor * value for value in self.values))

    def __matmul__(self, other):
        if isinstance(other, Matrix3):
            columns = other.columns
            return Matrix3.from_columns(self.apply_point(*column) for column in columns)
        return NotImplemented
