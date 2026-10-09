"""Matrix operations on 2×2 and 3×3 matrices, with step-by-step derivations.

A :class:`Derivation` is everything needed to explain an operation: the
operands, the result and an ordered list of :class:`Step` s. Each step says
which entries take part (for highlighting) and gives the arithmetic as text,
so the algebra view only draws what it is told.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.math_core.matrix3 import Matrix3

Matrix = Matrix2 | Matrix3
Cell = tuple[int, int]
_SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


class OperationKind(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    SCALE = "scale"
    MULTIPLY = "multiply"
    TRANSPOSE = "transpose"
    DETERMINANT = "determinant"

    @property
    def operand_count(self) -> int:
        return 2 if self in (OperationKind.ADD, OperationKind.SUBTRACT, OperationKind.MULTIPLY) else 1

    @property
    def needs_scalar(self) -> bool:
        return self is OperationKind.SCALE

    @property
    def gives_matrix(self) -> bool:
        return self is not OperationKind.DETERMINANT


# Labels for menus, with placeholder operand names.
OPERATION_LABELS = {
    OperationKind.ADD: "A + B",
    OperationKind.SUBTRACT: "A − B",
    OperationKind.SCALE: "k · A",
    OperationKind.MULTIPLY: "A · B",
    OperationKind.TRANSPOSE: "Aᵀ",
    OperationKind.DETERMINANT: "det A",
}


# Helpers ------------------------------------------------------------------------------


def identity(size: int) -> Matrix:
    return Matrix2.identity() if size == 2 else Matrix3.identity()


def from_rows(rows) -> Matrix:
    rows = [list(row) for row in rows]
    return Matrix2.from_rows(rows) if len(rows) == 2 else Matrix3.from_rows(rows)


def lerp(start: Matrix, end: Matrix, t: float) -> Matrix:
    """Entry-wise (1 − t)·start + t·end: every column moves on a straight line."""
    return from_rows(
        [(1.0 - t) * a + t * b for a, b in zip(row_a, row_b)] for row_a, row_b in zip(start.rows, end.rows)
    )


def number(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def factor(value: float) -> str:
    """A number inside a product, in parentheses when negative: ``(-2)``."""
    text = number(value)
    return f"({text})" if value < 0 else text


def entry_symbol(name: str, row: int, column: int) -> str:
    """``a₁₂`` for matrix ``A``; longer names keep their spelling: ``Rot₁₂``."""
    base = name.lower() if len(name) == 1 and name.isalpha() else name
    return base + f"{row + 1}{column + 1}".translate(_SUBSCRIPTS)


def cells(size: int) -> list[Cell]:
    return [(row, column) for row in range(size) for column in range(size)]


# Derivations ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mark:
    """One highlighted entry: in operand ``role`` ("left", "right" or "result")."""

    role: str
    row: int
    column: int
    # "active" entries are used by this step; "pivot" and "minor" are the parts
    # of a cofactor expansion term.
    kind: str = "active"


@dataclass(frozen=True)
class Step:
    marks: tuple[Mark, ...]
    formula: str
    # The result entry this step computes (revealed from this step on), if any.
    target: Cell | None = None


@dataclass(frozen=True)
class Derivation:
    kind: OperationKind
    operand_names: tuple[str, ...]
    operands: tuple[Matrix, ...]
    scalar: float | None
    result_name: str
    result: Matrix | float
    steps: tuple[Step, ...]

    @property
    def size(self) -> int:
        return self.operands[0].size

    @property
    def expression(self) -> str:
        """The operation in symbols, e.g. ``A · B`` or ``det A``."""
        names = self.operand_names
        if self.kind is OperationKind.ADD:
            return f"{names[0]} + {names[1]}"
        if self.kind is OperationKind.SUBTRACT:
            return f"{names[0]} − {names[1]}"
        if self.kind is OperationKind.SCALE:
            return f"{number(self.scalar)} · {names[0]}"
        if self.kind is OperationKind.MULTIPLY:
            return f"{names[0]} · {names[1]}"
        if self.kind is OperationKind.TRANSPOSE:
            return f"{names[0]}ᵀ"
        return f"det {names[0]}"

    @property
    def title(self) -> str:
        if self.kind is OperationKind.DETERMINANT:
            return f"{self.expression} = {number(self.result)}"
        return f"{self.result_name} = {self.expression}"


def compute(kind: OperationKind, operands: tuple[Matrix, ...], scalar: float | None = None) -> Matrix | float:
    check(kind, operands, scalar)
    first = operands[0]
    if kind is OperationKind.ADD:
        return first + operands[1]
    if kind is OperationKind.SUBTRACT:
        return first - operands[1]
    if kind is OperationKind.SCALE:
        return first.scaled(scalar)
    if kind is OperationKind.MULTIPLY:
        return first @ operands[1]
    if kind is OperationKind.TRANSPOSE:
        return first.transpose()
    return first.determinant


def check(kind: OperationKind, operands: tuple[Matrix, ...], scalar: float | None) -> None:
    """Raise ``ValueError`` with a user-facing reason if the operation is not defined."""
    if len(operands) != kind.operand_count:
        raise ValueError(f"{OPERATION_LABELS[kind]} needs {kind.operand_count} matrices")
    if kind.operand_count == 2 and operands[0].size != operands[1].size:
        sizes = " and ".join(f"{m.size}×{m.size}" for m in operands)
        raise ValueError(f"{OPERATION_LABELS[kind]} needs matrices of the same size, got {sizes}")
    if kind.needs_scalar and scalar is None:
        raise ValueError("k · A needs a number k")


def derive(
    kind: OperationKind,
    operand_names: tuple[str, ...],
    operands: tuple[Matrix, ...],
    scalar: float | None = None,
    result_name: str = "C",
) -> Derivation:
    """Compute the operation and explain it one step at a time."""
    result = compute(kind, operands, scalar)
    builders = {
        OperationKind.ADD: _entrywise_steps,
        OperationKind.SUBTRACT: _entrywise_steps,
        OperationKind.SCALE: _scale_steps,
        OperationKind.MULTIPLY: _multiply_steps,
        OperationKind.TRANSPOSE: _transpose_steps,
        OperationKind.DETERMINANT: _determinant_steps,
    }
    steps = builders[kind](kind, operand_names, operands, scalar, result_name, result)
    return Derivation(kind, tuple(operand_names), tuple(operands), scalar, result_name, result, tuple(steps))


def _entrywise_steps(kind, names, operands, _scalar, result_name, result):
    left, right = operands
    sign = "+" if kind is OperationKind.ADD else "−"
    steps = []
    for row, column in cells(left.size):
        a, b = left.entry(row, column), right.entry(row, column)
        formula = (
            f"{entry_symbol(result_name, row, column)} = {entry_symbol(names[0], row, column)} {sign} "
            f"{entry_symbol(names[1], row, column)} = {number(a)} {sign} {factor(b)} = "
            f"{number(result.entry(row, column))}"
        )
        marks = (Mark("left", row, column), Mark("right", row, column), Mark("result", row, column))
        steps.append(Step(marks, formula, (row, column)))
    return steps


def _scale_steps(_kind, names, operands, scalar, result_name, result):
    (matrix,) = operands
    steps = []
    for row, column in cells(matrix.size):
        formula = (
            f"{entry_symbol(result_name, row, column)} = {number(scalar)}·{entry_symbol(names[0], row, column)} = "
            f"{factor(scalar)}·{factor(matrix.entry(row, column))} = {number(result.entry(row, column))}"
        )
        steps.append(Step((Mark("left", row, column), Mark("result", row, column)), formula, (row, column)))
    return steps


def _multiply_steps(_kind, names, operands, _scalar, result_name, result):
    left, right = operands
    size = left.size
    steps = []
    for row, column in cells(size):
        symbols = " + ".join(
            f"{entry_symbol(names[0], row, k)}·{entry_symbol(names[1], k, column)}" for k in range(size)
        )
        values = " + ".join(f"{factor(left.entry(row, k))}·{factor(right.entry(k, column))}" for k in range(size))
        formula = (
            f"{entry_symbol(result_name, row, column)} = {symbols} = {values} = {number(result.entry(row, column))}"
        )
        marks = tuple(Mark("left", row, k) for k in range(size))
        marks += tuple(Mark("right", k, column) for k in range(size))
        marks += (Mark("result", row, column),)
        steps.append(Step(marks, formula, (row, column)))
    return steps


def _transpose_steps(_kind, names, operands, _scalar, result_name, result):
    (matrix,) = operands
    steps = []
    for row, column in cells(matrix.size):
        formula = (
            f"{entry_symbol(result_name, row, column)} = {entry_symbol(names[0], column, row)} = "
            f"{number(result.entry(row, column))}"
        )
        steps.append(Step((Mark("left", column, row), Mark("result", row, column)), formula, (row, column)))
    return steps


def _determinant_steps(_kind, names, operands, _scalar, _result_name, result):
    (matrix,) = operands
    name = names[0]
    if matrix.size == 2:
        a, b, c, d = matrix.entries
        e = lambda r, k: entry_symbol(name, r, k)  # noqa: E731
        return [
            Step(
                (Mark("left", 0, 0), Mark("left", 1, 1)),
                f"{e(0, 0)}·{e(1, 1)} = {factor(a)}·{factor(d)} = {number(a * d)}",
            ),
            Step(
                (Mark("left", 0, 1), Mark("left", 1, 0)),
                f"{e(0, 1)}·{e(1, 0)} = {factor(b)}·{factor(c)} = {number(b * c)}",
            ),
            Step(
                tuple(Mark("left", r, k) for r, k in cells(2)),
                f"det {name} = {e(0, 0)}{e(1, 1)} − {e(0, 1)}{e(1, 0)} = {number(a * d)} − {factor(b * c)} = "
                f"{number(result)}",
            ),
        ]

    # 3×3: cofactor expansion along the first row.
    steps = []
    terms = []
    for column in range(3):
        rows = [r for r in range(3) if r != 0]
        columns = [k for k in range(3) if k != column]
        (p, q), (r, s) = ([matrix.entry(i, j) for j in columns] for i in rows)
        minor = p * s - q * r
        sign = 1 if column % 2 == 0 else -1
        pivot = matrix.entry(0, column)
        term = sign * pivot * minor
        terms.append(term)
        marks = (Mark("left", 0, column, "pivot"),) + tuple(
            Mark("left", i, j, "minor") for i in rows for j in columns
        )
        sign_text = "+" if sign > 0 else "−"
        formula = (
            f"{sign_text} {entry_symbol(name, 0, column)}·det[{number(p)} {number(q)}; {number(r)} {number(s)}] = "
            f"{sign_text} {factor(pivot)}·({factor(p)}·{factor(s)} − {factor(q)}·{factor(r)}) = {number(term)}"
        )
        steps.append(Step(marks, formula))
    total = " + ".join(factor(term) for term in terms)
    steps.append(
        Step(tuple(Mark("left", r, k) for r, k in cells(3)), f"det {name} = {total} = {number(result)}")
    )
    return steps
