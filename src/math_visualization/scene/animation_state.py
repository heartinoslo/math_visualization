"""Renderer-independent animation state for the scene document."""

from __future__ import annotations

import math
from dataclasses import dataclass

from math_visualization.math_core.manim_port import DEFAULT_RATE_FUNCTION, RATE_FUNCTIONS
from math_visualization.math_core.transformations import INTERPOLATION_IDENTITY_TO_TARGET


PLAYBACK_SPEEDS = (0.25, 0.5, 1.0, 2.0)
INTERPOLATIONS = (INTERPOLATION_IDENTITY_TO_TARGET,)


@dataclass(frozen=True)
class AnimationState:
    """Animation settings and the elapsed fraction ``progress`` (τ) of the transformation.

    ``progress`` is time, not the eased parameter: the transformation uses
    ``t = rate_function(progress)``, as Manim does with ``rate_func``.
    """

    progress: float = 0.0
    duration: float = 2.0
    rate_function: str = DEFAULT_RATE_FUNCTION
    playback_speed: float = 1.0
    interpolation: str = INTERPOLATION_IDENTITY_TO_TARGET

    def __post_init__(self) -> None:
        if not math.isfinite(self.progress) or not 0.0 <= self.progress <= 1.0:
            raise ValueError(f"progress must be within [0, 1], got {self.progress!r}")
        if not math.isfinite(self.duration) or self.duration <= 0.0:
            raise ValueError(f"duration must be a positive finite number, got {self.duration!r}")
        if self.rate_function not in RATE_FUNCTIONS:
            raise ValueError(f"Unknown rate function: {self.rate_function!r}")
        if self.playback_speed not in PLAYBACK_SPEEDS:
            raise ValueError(f"playback_speed must be one of {PLAYBACK_SPEEDS}, got {self.playback_speed!r}")
        if self.interpolation not in INTERPOLATIONS:
            raise ValueError(f"Unknown interpolation: {self.interpolation!r}")
