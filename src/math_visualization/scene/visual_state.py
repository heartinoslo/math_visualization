"""Which transformation layers the renderers draw."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualState:
    show_transformed_grid: bool = True
    show_unit_square: bool = True
    show_basis_vectors: bool = True
    # Faint copies of the input vectors while a transformation is applied.
    show_ghosts: bool = True
    # Arc from î to ĵ showing the turning direction (orientation).
    show_orientation_arc: bool = True
    # Tint the unit square when det < 0 (orientation reversed).
    show_flip_tint: bool = True
    # The null space of a singular A: every input on it lands on the origin.
    show_kernel: bool = True

    def __post_init__(self) -> None:
        for name in VISUAL_FLAGS:
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean")


VISUAL_FLAGS = (
    "show_transformed_grid",
    "show_unit_square",
    "show_basis_vectors",
    "show_ghosts",
    "show_orientation_arc",
    "show_flip_tint",
    "show_kernel",
)
