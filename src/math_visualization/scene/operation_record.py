"""A matrix operation that was computed, kept so it can be replayed and explained."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from math_visualization.math_core.matrix_algebra import Derivation, Matrix, OperationKind, derive


@dataclass(frozen=True)
class OperationRecord:
    """``result_name = operation(operands)``, with the operands as they were when computed.

    Keeping the values (not just the names) means the replay always shows the
    computation that produced the result, even after the operands are edited
    or deleted. ``result_matrix_id`` names the matrix object that holds the
    result; a determinant has none.
    """

    object_id: str
    kind: OperationKind
    operand_names: tuple[str, ...]
    operands: tuple[Matrix, ...]
    scalar: float | None = None
    result_name: str = ""
    result_matrix_id: str | None = None

    @cached_property
    def derivation(self) -> Derivation:
        return derive(self.kind, self.operand_names, self.operands, self.scalar, self.result_name or "C")

    @property
    def title(self) -> str:
        return self.derivation.title

    @property
    def size(self) -> int:
        return self.operands[0].size
