"""Tests for Matrix2, the Manim port and the transformation animation model."""

import math

import pytest

from math_visualization.math_core import Matrix2, Vector2
from math_visualization.math_core.manim_port import RATE_FUNCTIONS, linear, smooth, straight_path
from math_visualization.math_core.transformations import (
    MATRIX_PRESETS,
    PRESETS_BY_KEY,
    ease,
    interpolate_from_identity,
)


E1, E2 = Vector2(1, 0), Vector2(0, 1)


def test_columns_are_the_images_of_the_standard_basis() -> None:
    matrix = Matrix2(1, 2, 3, 4)

    assert matrix @ E1 == matrix.first_column == Vector2(1, 3)
    assert matrix @ E2 == matrix.second_column == Vector2(2, 4)
    assert Matrix2.from_columns(Vector2(1, 3), Vector2(2, 4)) == matrix


def test_products_determinant_and_inverse() -> None:
    a = Matrix2(1, 2, 3, 4)
    b = Matrix2(0, -1, 1, 0)

    assert a @ b == Matrix2(2, -1, 4, -3)
    assert (a @ b) @ Vector2(1, 1) == a @ (b @ Vector2(1, 1))
    assert a.determinant == -2.0
    assert a @ a.inverse() == Matrix2.identity()


@pytest.mark.parametrize(
    ("matrix", "rank"),
    [
        (Matrix2(0, 0, 0, 0), 0),
        (Matrix2(1, 2, 2, 4), 1),
        (Matrix2(1, 0, 0, 0), 1),
        (Matrix2(1e-6, 0, 0, 1e-6), 2),
        (Matrix2(1e8, 1e8, 1e8, 1e8 + 1e-3), 1),
        (Matrix2(2, 0, 0, 0.5), 2),
    ],
)
def test_rank_is_scale_aware(matrix, rank) -> None:
    assert matrix.rank() == rank
    assert matrix.is_invertible() is (rank == 2)


def test_singular_inverse_is_rejected() -> None:
    with pytest.raises(ValueError):
        Matrix2(1, 2, 0.5, 1).inverse()


@pytest.mark.parametrize("value", [math.nan, math.inf, "1", True])
def test_rejects_non_finite_or_non_numeric_entries(value) -> None:
    with pytest.raises((TypeError, ValueError)):
        Matrix2(1, value, 0, 1)


def test_smooth_matches_manims_quintic_and_endpoints() -> None:
    for step in range(101):
        t = step / 100
        assert smooth(t) == pytest.approx(6 * t**5 - 15 * t**4 + 10 * t**3, abs=1e-12)
    assert (smooth(0.0), smooth(0.5), smooth(1.0)) == (0.0, 0.5, 1.0)
    assert linear(0.3) == 0.3
    assert set(RATE_FUNCTIONS) == {"smooth", "linear"}


def test_ease_rejects_unknown_rate_functions() -> None:
    assert ease(0.25, "linear") == 0.25
    with pytest.raises(ValueError):
        ease(0.5, "bounce")


def test_interpolation_runs_from_identity_to_target() -> None:
    target = Matrix2(0, -1, 1, 0)

    assert interpolate_from_identity(target, 0.0) == Matrix2.identity()
    assert interpolate_from_identity(target, 1.0) == target
    assert interpolate_from_identity(target, 0.5) == Matrix2(0.5, -0.5, 0.5, 0.5)


@pytest.mark.parametrize("t", [0.0, 0.2, 0.5, 0.9, 1.0])
def test_every_point_moves_on_manims_straight_path(t) -> None:
    target = Matrix2(2, 1, -1, 0.5)
    point = Vector2(1.5, -2.0)
    moved = interpolate_from_identity(target, t) @ point
    end = target @ point

    assert moved.x == pytest.approx(straight_path(point.x, end.x, t))
    assert moved.y == pytest.approx(straight_path(point.y, end.y, t))


def test_presets_are_unique_and_do_what_their_names_say() -> None:
    assert len(PRESETS_BY_KEY) == len(MATRIX_PRESETS)
    m = {key: preset.matrix for key, preset in PRESETS_BY_KEY.items()}

    assert m["identity"] == Matrix2.identity()
    assert m["scale"] @ Vector2(1, 1) == Vector2(2, 0.5)
    assert m["rotation"] @ E1 == E2 and m["rotation"] @ E2 == -E1
    assert m["shear"] @ E2 == Vector2(1, 1) and m["shear"] @ E1 == E1
    assert m["reflection"] @ Vector2(3, 2) == Vector2(3, -2)
    assert m["projection"] @ Vector2(3, 2) == Vector2(3, 0)
    assert m["projection"].rank() == 1
    assert m["singular"].rank() == 1 and m["singular"].determinant == 0.0
