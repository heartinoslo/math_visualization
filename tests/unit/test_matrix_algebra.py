"""Tests for 3×3 matrices, matrix operations and their step-by-step derivations."""

import random

import numpy as np
import pytest

from math_visualization.math_core import Matrix2
from math_visualization.math_core.matrix3 import Matrix3
from math_visualization.math_core.matrix_algebra import (
    OperationKind,
    compute,
    derive,
    entry_symbol,
    lerp,
    number,
)
from math_visualization.math_core.matrix_analysis import MatrixStatus, Orientation, analyze

A3 = Matrix3((1, 2, 3, 0, 1, 4, 5, 6, 0))
B3 = Matrix3((2, 0, 1, 1, 3, 0, 0, 1, 1))
A2 = Matrix2(1, 2, 3, 4)
B2 = Matrix2(0, 1, -1, 2)


def random_matrix3(generator) -> Matrix3:
    return Matrix3(tuple(generator.uniform(-3, 3) for _ in range(9)))


# Matrix3 -------------------------------------------------------------------------------------


def test_matrix3_matches_numpy() -> None:
    generator = random.Random(3)
    for _ in range(50):
        a, b = random_matrix3(generator), random_matrix3(generator)
        na, nb = np.array(a.rows), np.array(b.rows)
        assert np.allclose(np.array((a @ b).rows), na @ nb)
        assert np.allclose(np.array((a + b).rows), na + nb)
        assert np.allclose(np.array((a - b).rows), na - nb)
        assert np.allclose(np.array(a.transpose().rows), na.T)
        assert a.determinant == pytest.approx(np.linalg.det(na))
        assert np.allclose(np.array((a @ a.inverse()).rows), np.eye(3), atol=1e-9)


def test_matrix3_rank_and_validation() -> None:
    assert Matrix3.identity().rank() == 3
    assert Matrix3((1, 2, 3, 2, 4, 6, 0, 0, 1)).rank() == 2
    assert Matrix3((1, 2, 3, 2, 4, 6, 3, 6, 9)).rank() == 1
    assert Matrix3((0,) * 9).rank() == 0
    assert Matrix3.from_columns([(1, 0, 0), (0, 2, 0), (0, 0, 3)]).columns == ((1, 0, 0), (0, 2, 0), (0, 0, 3))
    with pytest.raises(ValueError):
        Matrix3((1, 2, 3))
    with pytest.raises(ValueError):
        Matrix3((float("nan"),) * 9)
    with pytest.raises(ValueError):
        Matrix3((1, 2, 3, 2, 4, 6, 3, 6, 9)).inverse()


def test_analysis_covers_3x3() -> None:
    result = analyze(A3)
    assert result.determinant == pytest.approx(1.0)
    assert result.is_invertible and result.orientation is Orientation.PRESERVED
    assert analyze(Matrix3((1, 0, 0, 0, 1, 0, 0, 0, -2))).orientation is Orientation.REVERSED
    singular = analyze(Matrix3((1, 2, 3, 2, 4, 6, 0, 0, 1)))
    assert singular.status is MatrixStatus.SINGULAR and singular.rank == 2
    assert singular.image_direction is None and singular.kernel_direction is None


# Operations ------------------------------------------------------------------------------------


def test_compute_operations() -> None:
    assert compute(OperationKind.ADD, (A2, B2)) == Matrix2(1, 3, 2, 6)
    assert compute(OperationKind.SUBTRACT, (A2, B2)) == Matrix2(1, 1, 4, 2)
    assert compute(OperationKind.SCALE, (A2,), 2.0) == Matrix2(2, 4, 6, 8)
    assert compute(OperationKind.MULTIPLY, (A2, B2)) == Matrix2(-2, 5, -4, 11)
    assert compute(OperationKind.TRANSPOSE, (A2,)) == Matrix2(1, 3, 2, 4)
    assert compute(OperationKind.DETERMINANT, (A2,)) == -2.0
    assert compute(OperationKind.DETERMINANT, (A3,)) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("kind", "operands", "scalar", "message"),
    [
        (OperationKind.ADD, (A2, A3), None, "same size"),
        (OperationKind.MULTIPLY, (A3, B2), None, "same size"),
        (OperationKind.SCALE, (A2,), None, "number k"),
        (OperationKind.TRANSPOSE, (A2, B2), None, "needs 1"),
    ],
)
def test_undefined_operations_explain_why(kind, operands, scalar, message) -> None:
    with pytest.raises(ValueError, match=message):
        compute(kind, operands, scalar)


def test_entry_symbols() -> None:
    assert entry_symbol("A", 0, 1) == "a₁₂"
    assert entry_symbol("Rot", 2, 2) == "Rot₃₃"


# Derivations -------------------------------------------------------------------------------------


def test_multiplication_steps_are_row_times_column() -> None:
    derivation = derive(OperationKind.MULTIPLY, ("A", "B"), (A2, B2))

    assert derivation.title == "C = A · B"
    assert len(derivation.steps) == 4
    step = derivation.steps[1]
    assert step.target == (0, 1)
    assert step.formula == "c₁₂ = a₁₁·b₁₂ + a₁₂·b₂₂ = 1·1 + 2·2 = 5"
    left = {(m.row, m.column) for m in step.marks if m.role == "left"}
    right = {(m.row, m.column) for m in step.marks if m.role == "right"}
    assert left == {(0, 0), (0, 1)} and right == {(0, 1), (1, 1)}


@pytest.mark.parametrize("size", [2, 3])
@pytest.mark.parametrize(
    "kind", [OperationKind.ADD, OperationKind.SUBTRACT, OperationKind.SCALE, OperationKind.MULTIPLY, OperationKind.TRANSPOSE]
)
def test_every_result_entry_is_computed_once_and_matches(kind, size) -> None:
    first, second = (A2, B2) if size == 2 else (A3, B3)
    operands = (first, second) if kind.operand_count == 2 else (first,)
    derivation = derive(kind, ("A", "B")[: kind.operand_count], operands, -1.5 if kind.needs_scalar else None)

    targets = [step.target for step in derivation.steps]
    assert sorted(targets) == [(r, c) for r in range(size) for c in range(size)]
    for step in derivation.steps:
        value = derivation.result.entry(*step.target)
        # The formula ends with the value it computes.
        assert step.formula.endswith("= " + number(value))


def test_negative_numbers_are_parenthesised_in_products() -> None:
    step = derive(OperationKind.MULTIPLY, ("A", "B"), (A2, B2)).steps[2]
    assert step.formula == "c₂₁ = a₂₁·b₁₁ + a₂₂·b₂₁ = 3·0 + 4·(-1) = -4"


def test_transpose_steps_read_across_the_diagonal() -> None:
    step = derive(OperationKind.TRANSPOSE, ("A",), (A2,)).steps[1]
    assert step.formula == "c₁₂ = a₂₁ = 3"
    assert [(m.role, m.row, m.column) for m in step.marks] == [("left", 1, 0), ("result", 0, 1)]


def test_2x2_determinant_steps() -> None:
    derivation = derive(OperationKind.DETERMINANT, ("A",), (A2,))
    assert derivation.title == "det A = -2"
    assert [step.formula for step in derivation.steps] == [
        "a₁₁·a₂₂ = 1·4 = 4",
        "a₁₂·a₂₁ = 2·3 = 6",
        "det A = a₁₁a₂₂ − a₁₂a₂₁ = 4 − 6 = -2",
    ]


def test_3x3_determinant_is_a_cofactor_expansion_along_the_first_row() -> None:
    derivation = derive(OperationKind.DETERMINANT, ("A",), (A3,))
    steps = derivation.steps

    assert len(steps) == 4
    first = steps[0]
    assert {(m.row, m.column) for m in first.marks if m.kind == "pivot"} == {(0, 0)}
    assert {(m.row, m.column) for m in first.marks if m.kind == "minor"} == {(1, 1), (1, 2), (2, 1), (2, 2)}
    assert first.formula == "+ a₁₁·det[1 4; 6 0] = + 1·(1·0 − 4·6) = -24"
    assert steps[1].formula.startswith("− a₁₂·det[0 4; 5 0]")
    assert steps[-1].formula == "det A = (-24) + 40 + (-15) = 1"


def test_lerp_moves_entries_on_straight_lines() -> None:
    halfway = lerp(Matrix3.identity(), A3, 0.5)
    assert halfway.entry(0, 1) == pytest.approx(1.0) and halfway.entry(0, 0) == pytest.approx(1.0)
    assert lerp(A2, B2, 1.0) == B2
