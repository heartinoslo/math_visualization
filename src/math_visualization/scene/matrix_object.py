"""Named matrices stored in the scene document."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.scene.vector_object import MAX_NAME_LENGTH, new_object_id

# Capital letters in order; I is left out because it names the identity matrix.
MATRIX_NAME_SEQUENCE = tuple("ABCDEFGHJKLMNPQRSTUVWXYZ")
_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
# Only 2×2 for now; the size is stored so 3×3 matrices can join later.
SUPPORTED_SIZES = (2,)

__all__ = ["MATRIX_NAME_SEQUENCE", "MatrixObject", "new_object_id", "next_matrix_name"]


def next_matrix_name(existing: Iterable[str]) -> str:
    """Return the first free name in A, B, C, …, H, J, …, then A₁, B₁, …"""
    taken = set(existing)
    round_index = 0
    while True:
        suffix = str(round_index).translate(_SUBSCRIPT_DIGITS) if round_index else ""
        for letter in MATRIX_NAME_SEQUENCE:
            candidate = letter + suffix
            if candidate not in taken:
                return candidate
        round_index += 1


@dataclass(frozen=True)
class MatrixObject:
    """A named transformation matrix."""

    object_id: str
    name: str
    matrix: Matrix2

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("name must not be empty")
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"name must be at most {MAX_NAME_LENGTH} characters")
        if not isinstance(self.matrix, Matrix2):
            raise TypeError("matrix must be a Matrix2")
        object.__setattr__(self, "name", name)

    @property
    def size(self) -> int:
        return 2
