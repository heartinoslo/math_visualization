"""Named, coloured vectors stored in the scene document."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import uuid4

from math_visualization.math_core.vector2 import Vector2


# Mathematical naming order. x, y, z, i and j are left out because they name
# axes and basis vectors; o is left out because it reads like 0.
VECTOR_NAME_SEQUENCE = tuple("uvwabcdefghklmnpqrst")
_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

# Distinct from the red/green/blue axis colours and readable on dark and light.
VECTOR_PALETTE = (
    "#F59E0B",
    "#A78BFA",
    "#22D3EE",
    "#F472B6",
    "#84CC16",
    "#FB7185",
    "#2DD4BF",
    "#EAB308",
)

MAX_NAME_LENGTH = 24
_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def new_object_id() -> str:
    return uuid4().hex


def next_vector_name(existing: Iterable[str]) -> str:
    """Return the first free name in u, v, w, a, b, …, then u₁, v₁, …"""
    taken = set(existing)
    round_index = 0
    while True:
        suffix = str(round_index).translate(_SUBSCRIPT_DIGITS) if round_index else ""
        for letter in VECTOR_NAME_SEQUENCE:
            candidate = letter + suffix
            if candidate not in taken:
                return candidate
        round_index += 1


def next_vector_color(existing: Iterable[str]) -> str:
    """Return the least-used palette colour, preferring palette order on ties."""
    counts = {color: 0 for color in VECTOR_PALETTE}
    for color in existing:
        if color.upper() in counts:
            counts[color.upper()] += 1
    return min(VECTOR_PALETTE, key=lambda color: counts[color])


@dataclass(frozen=True)
class VectorObject:
    """A vector drawn from the origin, with its display identity."""

    object_id: str
    name: str
    color: str
    vector: Vector2

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("name must not be empty")
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"name must be at most {MAX_NAME_LENGTH} characters")
        if not _COLOR_PATTERN.match(self.color):
            raise ValueError(f"color must look like #RRGGBB, got {self.color!r}")
        if not isinstance(self.vector, Vector2):
            raise TypeError("vector must be a Vector2")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "color", self.color.upper())
