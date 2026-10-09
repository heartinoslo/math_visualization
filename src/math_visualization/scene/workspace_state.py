"""Renderer-independent workspace and camera state for the scene document."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class WorkspaceMode(StrEnum):
    """Visualization workspace used to observe the mathematical scene."""

    TWO_D = "2d"
    THREE_D = "3d"
    ALGEBRA = "algebra"


class ProjectionMode(StrEnum):
    """Projection used by the 3D workspace camera."""

    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")


@dataclass(frozen=True)
class CameraState2D:
    """Pan and zoom of the 2D workspace, in mathematical coordinates."""

    center_x: float = 0.0
    center_y: float = 0.0
    zoom: float = 1.0

    def __post_init__(self) -> None:
        _require_finite("center_x", self.center_x)
        _require_finite("center_y", self.center_y)
        _require_finite("zoom", self.zoom)
        if self.zoom <= 0.0:
            raise ValueError(f"zoom must be positive, got {self.zoom!r}")


@dataclass(frozen=True)
class CameraState3D:
    """Orbit camera of the 3D workspace; angles are in degrees."""

    target_x: float = 0.0
    target_y: float = 0.0
    target_z: float = 0.0
    azimuth: float = -60.0
    elevation: float = 25.0
    distance: float = 12.0
    projection_mode: ProjectionMode = ProjectionMode.PERSPECTIVE

    def __post_init__(self) -> None:
        for name in ("target_x", "target_y", "target_z", "azimuth", "elevation", "distance"):
            _require_finite(name, getattr(self, name))
        if not -90.0 <= self.elevation <= 90.0:
            raise ValueError(f"elevation must be within [-90, 90], got {self.elevation!r}")
        if self.distance <= 0.0:
            raise ValueError(f"distance must be positive, got {self.distance!r}")
        # Accept plain strings from callers while always storing the enum.
        object.__setattr__(self, "projection_mode", ProjectionMode(self.projection_mode))
