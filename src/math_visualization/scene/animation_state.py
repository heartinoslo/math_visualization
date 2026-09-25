"""Renderer-independent animation state for the scene document."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AnimationState:
    """Normalized animation progress and its playback duration in seconds."""

    progress: float = 0.0
    duration: float = 2.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.progress) or not 0.0 <= self.progress <= 1.0:
            raise ValueError(f"progress must be within [0, 1], got {self.progress!r}")
        if not math.isfinite(self.duration) or self.duration <= 0.0:
            raise ValueError(f"duration must be a positive finite number, got {self.duration!r}")
