"""Tests for the Vector2 value type and the shared tolerance policy."""

import math

import pytest

from math_visualization.math_core import ABSOLUTE_TOLERANCE, Vector2, is_zero


def test_length_and_direction() -> None:
    vector = Vector2(3, 4)

    assert vector.length == 5.0
    assert vector.angle_degrees == pytest.approx(math.degrees(math.atan2(4, 3)))
    assert Vector2(-1, 0).angle_degrees == 180.0
    assert Vector2(0, -2).angle_degrees == -90.0


def test_arithmetic_and_dot_product() -> None:
    a = Vector2(1, 2)
    b = Vector2(-3, 0.5)

    assert a + b == Vector2(-2, 2.5)
    assert a - b == Vector2(4, 1.5)
    assert 2 * a == a * 2 == Vector2(2, 4)
    assert -a == Vector2(-1, -2)
    assert a.dot(b) == pytest.approx(-2.0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_non_finite_components(value) -> None:
    with pytest.raises(ValueError):
        Vector2(value, 0.0)


@pytest.mark.parametrize("value", ["1", None, True])
def test_rejects_non_numeric_components(value) -> None:
    with pytest.raises(TypeError):
        Vector2(0.0, value)


def test_zero_uses_the_shared_tolerance_and_negative_zero_is_folded() -> None:
    assert Vector2(0, 0).is_zero()
    assert Vector2(ABSOLUTE_TOLERANCE / 2, 0).is_zero()
    assert not Vector2(1e-6, 0).is_zero()
    assert Vector2(0, 0).angle_degrees == 0.0
    assert math.copysign(1.0, Vector2(-0.0, 0.0).x) == 1.0
    assert is_zero(-1e-12) and not is_zero(1e-3)
