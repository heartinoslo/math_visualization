"""Immutable real 2×2 matrix."""

from __future__ import annotations

import math
from dataclasses import dataclass

from math_visualization.math_core.tolerances import ABSOLUTE_TOLERANCE, SINGULAR_RATIO
from math_visualization.math_core.vector2 import Vector2


@dataclass(frozen=True)
class Matrix2:
    """The matrix ``[[a, b], [c, d]]``; its columns are the images of e₁ and e₂."""

    a: float
    b: float
    c: float
    d: float

    def __post_init__(self) -> None:
        for name in ("a", "b", "c", "d"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number, got {value!r}")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
            object.__setattr__(self, name, float(value) + 0.0)

    @classmethod
    def identity(cls) -> Matrix2:
        return cls(1.0, 0.0, 0.0, 1.0)

    @classmethod
    def from_columns(cls, first: Vector2, second: Vector2) -> Matrix2:
        return cls(first.x, second.x, first.y, second.y)

    @property
    def entries(self) -> tuple[float, float, float, float]:
        """Row-major entries ``(a, b, c, d)``."""
        return (self.a, self.b, self.c, self.d)

    @property
    def rows(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return ((self.a, self.b), (self.c, self.d))

    @property
    def first_column(self) -> Vector2:
        return Vector2(self.a, self.c)

    @property
    def second_column(self) -> Vector2:
        return Vector2(self.b, self.d)

    @property
    def determinant(self) -> float:
        return self.a * self.d - self.b * self.c

    @property
    def frobenius_norm(self) -> float:
        return math.sqrt(self.a**2 + self.b**2 + self.c**2 + self.d**2)

    @property
    def singular_values(self) -> tuple[float, float]:
        """``(σ_max, σ_min)``, computed without catastrophic cancellation.

        σ_max² = (‖A‖² + √D) / 2 with D = ‖A‖⁴ − 4·det². D is evaluated as the
        product ((a−d)² + (b+c)²)·((a+d)² + (b−c)²), which equals it exactly
        but never subtracts nearly equal numbers; σ_min then follows as
        |det| / σ_max.
        """
        a, b, c, d = self.entries
        frobenius_squared = a * a + b * b + c * c + d * d
        discriminant = ((a - d) ** 2 + (b + c) ** 2) * ((a + d) ** 2 + (b - c) ** 2)
        largest = math.sqrt((frobenius_squared + math.sqrt(discriminant)) / 2.0)
        if largest == 0.0:
            return (0.0, 0.0)
        return (largest, min(largest, abs(self.determinant) / largest))

    def rank(self, tolerance: float = ABSOLUTE_TOLERANCE, ratio: float = SINGULAR_RATIO) -> int:
        """Rank with a scale-invariant singularity test.

        σ_min / σ_max does not change when the matrix is scaled, so a tiny
        invertible matrix (1e-6·I) and a huge near-singular one are both
        classified by shape rather than by size. Only the all-zero test is
        absolute.
        """
        largest, smallest = self.singular_values
        if largest <= tolerance:
            return 0
        if smallest <= ratio * largest:
            return 1
        return 2

    def is_invertible(self, tolerance: float = ABSOLUTE_TOLERANCE) -> bool:
        return self.rank(tolerance) == 2

    def inverse(self) -> Matrix2:
        if not self.is_invertible():
            raise ValueError("A singular matrix has no inverse")
        det = self.determinant
        return Matrix2(self.d / det, -self.b / det, -self.c / det, self.a / det)

    def apply(self, vector: Vector2) -> Vector2:
        return Vector2(self.a * vector.x + self.b * vector.y, self.c * vector.x + self.d * vector.y)

    def apply_point(self, x: float, y: float) -> tuple[float, float]:
        """Fast path for geometry: transform a raw point without building objects."""
        return (self.a * x + self.b * y, self.c * x + self.d * y)

    def __matmul__(self, other):
        if isinstance(other, Vector2):
            return self.apply(other)
        if isinstance(other, Matrix2):
            return Matrix2(
                self.a * other.a + self.b * other.c,
                self.a * other.b + self.b * other.d,
                self.c * other.a + self.d * other.c,
                self.c * other.b + self.d * other.d,
            )
        return NotImplemented
