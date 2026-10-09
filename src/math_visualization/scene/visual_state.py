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

    def __post_init__(self) -> None:
        for name in VISUAL_FLAGS:
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean")


VISUAL_FLAGS = ("show_transformed_grid", "show_unit_square", "show_basis_vectors", "show_ghosts")
