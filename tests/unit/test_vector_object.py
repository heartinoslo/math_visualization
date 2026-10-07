"""Tests for scene vectors, naming and colour assignment."""

import pytest

from math_visualization.math_core import Vector2
from math_visualization.scene.vector_object import (
    VECTOR_NAME_SEQUENCE,
    VECTOR_PALETTE,
    VectorObject,
    next_vector_color,
    next_vector_name,
)


def test_names_follow_mathematical_order_and_skip_axis_letters() -> None:
    assert VECTOR_NAME_SEQUENCE[:5] == ("u", "v", "w", "a", "b")
    assert not {"x", "y", "z", "i", "j", "o"} & set(VECTOR_NAME_SEQUENCE)
    assert next_vector_name([]) == "u"
    assert next_vector_name(["u", "v"]) == "w"
    assert next_vector_name(["v"]) == "u"


def test_names_continue_with_subscripts_when_letters_run_out() -> None:
    assert next_vector_name(VECTOR_NAME_SEQUENCE) == "u₁"
    assert next_vector_name([*VECTOR_NAME_SEQUENCE, "u₁"]) == "v₁"


def test_colours_prefer_unused_palette_entries() -> None:
    assert next_vector_color([]) == VECTOR_PALETTE[0]
    assert next_vector_color([VECTOR_PALETTE[0].lower()]) == VECTOR_PALETTE[1]
    assert next_vector_color(VECTOR_PALETTE) == VECTOR_PALETTE[0]


def test_vector_object_normalizes_and_validates() -> None:
    vector = VectorObject("id", "  w ", "#aabbcc", Vector2(1, 2))

    assert (vector.name, vector.color) == ("w", "#AABBCC")
    for name, color in (("", "#AABBCC"), ("v", "red"), ("v" * 25, "#AABBCC")):
        with pytest.raises(ValueError):
            VectorObject("id", name, color, Vector2(0, 0))
