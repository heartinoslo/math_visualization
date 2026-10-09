"""Tests for determinant, rank, orientation and invertibility of 2×2 matrices."""

import math
import random

import pytest

from math_visualization.math_core import Matrix2
from math_visualization.math_core.matrix_analysis import MatrixStatus, Orientation, analyze
from math_visualization.math_core.tolerances import NEAR_SINGULAR_RATIO
from math_visualization.viewport.transformation_geometry import (
    line_through_origin,
    orientation_arc,
    ribbon,
    unit_square,
)


def random_matrices(count=200, seed=6):
    generator = random.Random(seed)
    return [Matrix2(*(generator.uniform(-3, 3) for _ in range(4))) for _ in range(count)]


def shoelace(points) -> float:
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))


# Typical matrices -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("matrix", "determinant", "orientation", "condition"),
    [
        (Matrix2.identity(), 1.0, Orientation.PRESERVED, 1.0),
        (Matrix2(2, 0, 0, 0.5), 1.0, Orientation.PRESERVED, 4.0),
        (Matrix2(0, -1, 1, 0), 1.0, Orientation.PRESERVED, 1.0),
        (Matrix2(1, 1, 0, 1), 1.0, Orientation.PRESERVED, (3 + math.sqrt(5)) / 2),
        (Matrix2(1, 0, 0, -1), -1.0, Orientation.REVERSED, 1.0),
        (Matrix2(3, 1, 1, 2), 5.0, Orientation.PRESERVED, None),
        (Matrix2(1, 2, 3, 4), -2.0, Orientation.REVERSED, None),
    ],
)
def test_typical_matrices(matrix, determinant, orientation, condition) -> None:
    result = analyze(matrix)

    assert result.determinant == pytest.approx(determinant)
    assert result.area_scale == pytest.approx(abs(determinant))
    assert result.orientation is orientation
    assert result.rank == 2 and result.is_invertible
    assert result.status is MatrixStatus.REGULAR
    assert (result.inverse @ matrix).entries == pytest.approx((1, 0, 0, 1), abs=1e-12)
    assert result.image_direction is None and result.kernel_direction is None
    if condition is not None:
        assert result.condition_number == pytest.approx(condition)


def test_unit_square_area_is_the_absolute_determinant_and_its_sign_the_orientation() -> None:
    for matrix in random_matrices():
        signed_area = shoelace(unit_square(matrix))
        result = analyze(matrix)
        assert abs(signed_area) == pytest.approx(result.area_scale, abs=1e-12)
        if result.orientation is Orientation.PRESERVED:
            assert signed_area > 0
        elif result.orientation is Orientation.REVERSED:
            assert signed_area < 0


# Singular matrices ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("matrix", "image"),
    [
        (Matrix2(1, 0, 0, 0), (1.0, 0.0)),
        (Matrix2(1, 2, 0.5, 1), (2.0, 1.0)),
        (Matrix2(0, 0, 3, -6), (0.0, 1.0)),
        (Matrix2(1e8, 1e8, 1e8, 1e8), (1.0, 1.0)),
    ],
)
def test_rank_one_collapses_onto_a_line_with_a_kernel(matrix, image) -> None:
    result = analyze(matrix)

    assert result.rank == 1 and not result.is_invertible
    assert result.status is MatrixStatus.SINGULAR
    assert result.orientation is Orientation.COLLAPSED
    assert result.inverse is None and result.condition_number == math.inf
    direction = result.image_direction
    norm = math.hypot(*image)
    assert abs(direction.x * image[1] - direction.y * image[0]) / norm < 1e-12
    assert direction.length == pytest.approx(1.0)
    kernel = result.kernel_direction
    assert kernel.length == pytest.approx(1.0)
    assert (matrix @ kernel).length <= 1e-9 * matrix.frobenius_norm


def test_zero_matrix_collapses_to_the_origin() -> None:
    result = analyze(Matrix2(0, 0, 0, 0))

    assert result.rank == 0 and result.status is MatrixStatus.SINGULAR
    assert result.orientation is Orientation.COLLAPSED
    assert result.area_scale == 0.0
    assert result.image_direction is None and result.kernel_direction is None


def test_singularity_is_not_an_exact_float_comparison() -> None:
    # 0.1 and 0.3 are not exact in binary, so det is a rounding residue, not 0.
    matrix = Matrix2(0.1, 0.3, 1.0, 3.0)
    assert matrix.determinant != 0.0
    assert analyze(matrix).status is MatrixStatus.SINGULAR


# Near-singular matrices ---------------------------------------------------------------


def test_near_singular_is_invertible_but_flagged() -> None:
    matrix = Matrix2(1, 2, 0.5, 1.0001)
    result = analyze(matrix)

    assert result.is_invertible and result.rank == 2
    assert result.status is MatrixStatus.NEAR_SINGULAR
    assert result.orientation is Orientation.PRESERVED
    assert result.condition_number > 1 / NEAR_SINGULAR_RATIO
    assert (result.inverse @ matrix).entries == pytest.approx((1, 0, 0, 1), abs=1e-8)


@pytest.mark.parametrize("scale", [1e-6, 1.0, 1e6])
def test_status_is_scale_invariant(scale) -> None:
    def status(a, b, c, d):
        return analyze(Matrix2(a * scale, b * scale, c * scale, d * scale)).status

    assert status(1, 0, 0, 1) is MatrixStatus.REGULAR
    assert status(1, 0, 0, 0.999e-3) is MatrixStatus.NEAR_SINGULAR
    assert status(1, 0, 0, 1.001e-3) is MatrixStatus.REGULAR
    assert status(1, 2, 0.5, 1) is MatrixStatus.SINGULAR


def test_every_property_follows_the_same_rank() -> None:
    generator = random.Random(11)
    matrices = random_matrices()
    # Exactly and nearly singular ones too: column 2 = k·column 1 (+ noise).
    for _ in range(100):
        x, y, k = (generator.uniform(-3, 3) for _ in range(3))
        noise = generator.choice([0.0, 1e-13, 1e-6, 1e-2])
        matrices.append(Matrix2(x, k * x + noise, y, k * y))
    for matrix in matrices:
        result = analyze(matrix)
        invertible = result.rank == 2
        assert result.is_invertible is invertible
        assert (result.inverse is not None) is invertible
        assert (result.orientation is not Orientation.COLLAPSED) is invertible
        assert (result.status is MatrixStatus.SINGULAR) is (not invertible)
        assert matrix.is_invertible() is invertible


# Geometry for the visual feedback -------------------------------------------------------


def angle_of(point) -> float:
    return math.atan2(point[1], point[0])


@pytest.mark.parametrize(
    ("matrix", "turn"),
    [(Matrix2.identity(), 1), (Matrix2(1, 0, 0, -1), -1), (Matrix2(1, 2, 3, 4), -1), (Matrix2(2, -1, 1, 3), 1)],
)
def test_orientation_arc_turns_from_the_first_column_to_the_second(matrix, turn) -> None:
    arc, head = orientation_arc(matrix, radius=0.5, head_length=0.1, head_half_width=0.04)

    first, second = matrix.first_column, matrix.second_column
    assert angle_of(arc[0]) == pytest.approx(math.atan2(first.y, first.x))
    assert angle_of(head[0]) == pytest.approx(math.atan2(second.y, second.x))
    assert all(math.hypot(*p) == pytest.approx(0.5) for p in arc)
    for (x1, y1), (x2, y2) in zip(arc, arc[1:]):
        assert (x1 * y2 - x2 * y1) * turn > 0


def test_orientation_arc_needs_two_independent_columns() -> None:
    assert orientation_arc(Matrix2(1, 2, 0.5, 1), 0.5, 0.1, 0.04) is None
    assert orientation_arc(Matrix2(0, 0, 0, 0), 0.5, 0.1, 0.04) is None


def test_arc_head_is_shortened_on_a_small_sweep() -> None:
    nearly_parallel = Matrix2(1, 1, 0, 0.05)
    arc, head = orientation_arc(nearly_parallel, radius=1.0, head_length=0.5, head_half_width=0.2)
    sweep = math.atan2(nearly_parallel.determinant, nearly_parallel.first_column.dot(nearly_parallel.second_column))

    assert math.dist(arc[-1], head[0]) <= 0.5 * abs(sweep) + 1e-12


def test_line_through_origin_and_ribbon() -> None:
    assert line_through_origin((0.6, 0.8), 5.0) == ((-3.0, -4.0), (3.0, 4.0))
    triangles = ribbon([(0.0, 0.0), (2.0, 0.0), (2.0, 0.0)], 0.5)
    assert len(triangles) == 6
    assert {y for _, y in triangles} == {0.5, -0.5}
