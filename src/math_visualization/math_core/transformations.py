"""Linear transformation animation and the matrix presets.

The animation follows Manim's ``ApplyMatrix``: every point travels on a
straight line from ``p`` to ``A p``, i.e. ``p(t) = (1 - t) p + t A p``, which is
``A(t) = (1 - t) I + t A`` applied to ``p``. ``t`` is the eased progress
``rate(τ)`` of the elapsed fraction ``τ``. This is the first interpolation
path offered, not the only mathematical reading of "transforming".
"""

from __future__ import annotations

from dataclasses import dataclass

from math_visualization.math_core.manim_port import RATE_FUNCTIONS, straight_path
from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.math_core.matrix3 import Matrix3


INTERPOLATION_IDENTITY_TO_TARGET = "identity_to_target"


def ease(progress: float, rate_function: str) -> float:
    """Map elapsed fraction ``τ`` to animation parameter ``t`` with a Manim rate function."""
    try:
        return RATE_FUNCTIONS[rate_function](progress)
    except KeyError:
        raise ValueError(f"Unknown rate function: {rate_function!r}") from None


def interpolate_from_identity(target: Matrix2, t: float) -> Matrix2:
    """``A(t) = (1 - t) I + t A``, entry by entry along Manim's straight path."""
    identity = Matrix2.identity()
    return Matrix2(
        *(straight_path(start, end, t) for start, end in zip(identity.entries, target.entries))
    )


@dataclass(frozen=True)
class MatrixPreset:
    key: str
    label: str
    matrix: Matrix2


MATRIX_PRESETS: tuple[MatrixPreset, ...] = (
    MatrixPreset("identity", "Identity", Matrix2(1, 0, 0, 1)),
    MatrixPreset("scale", "Scale", Matrix2(2, 0, 0, 0.5)),
    MatrixPreset("rotation", "Rotate 90°", Matrix2(0, -1, 1, 0)),
    MatrixPreset("shear", "Shear", Matrix2(1, 1, 0, 1)),
    MatrixPreset("reflection", "Reflect (x-axis)", Matrix2(1, 0, 0, -1)),
    MatrixPreset("projection", "Project (x-axis)", Matrix2(1, 0, 0, 0)),
    MatrixPreset("singular", "Singular", Matrix2(1, 2, 0.5, 1)),
)

PRESETS_BY_KEY = {preset.key: preset for preset in MATRIX_PRESETS}


@dataclass(frozen=True)
class Matrix3Preset:
    key: str
    label: str
    matrix: Matrix3


MATRIX3_PRESETS: tuple[Matrix3Preset, ...] = (
    Matrix3Preset("identity", "Identity", Matrix3.identity()),
    Matrix3Preset("scale", "Scale", Matrix3((2, 0, 0, 0, 1, 0, 0, 0, 0.5))),
    Matrix3Preset("rotation_z", "Rotate z 90°", Matrix3((0, -1, 0, 1, 0, 0, 0, 0, 1))),
    Matrix3Preset("rotation_x", "Rotate x 90°", Matrix3((1, 0, 0, 0, 0, -1, 0, 1, 0))),
    Matrix3Preset("shear", "Shear", Matrix3((1, 0, 1, 0, 1, 0, 0, 0, 1))),
    Matrix3Preset("projection", "Project (xy)", Matrix3((1, 0, 0, 0, 1, 0, 0, 0, 0))),
    Matrix3Preset("singular", "Singular", Matrix3((1, 2, 3, 0, 1, 1, 1, 3, 4))),
)

PRESETS3_BY_KEY = {preset.key: preset for preset in MATRIX3_PRESETS}
