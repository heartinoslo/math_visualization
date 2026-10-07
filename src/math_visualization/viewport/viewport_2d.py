"""Pure 2D viewport mathematics: coordinate mapping, pan, zoom and grid layout.

Mathematical coordinates have ``y`` pointing up; screen coordinates are logical
pixels with the origin at the top-left corner and ``y`` pointing down. The
camera centre is always drawn at the middle of the viewport.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from math_visualization.scene.workspace_state import CameraState2D


BASE_PIXELS_PER_UNIT = 80.0
MIN_ZOOM = 1e-3
MAX_ZOOM = 1e3
MIN_MAJOR_SPACING_PX = 80.0
# Upper bound per axis and layer; normal viewports need far fewer lines.
MAX_LINES_PER_AXIS = 512


def clamp_zoom(zoom: float) -> float:
    """Return ``zoom`` limited to the supported ``[MIN_ZOOM, MAX_ZOOM]`` range."""
    return min(max(zoom, MIN_ZOOM), MAX_ZOOM)


@dataclass(frozen=True)
class GridStep:
    """Major grid spacing ``mantissa * 10**exponent`` and its minor subdivisions."""

    mantissa: int
    exponent: int

    @property
    def major(self) -> float:
        return self.mantissa * 10.0**self.exponent

    @property
    def subdivisions(self) -> int:
        return 4 if self.mantissa == 2 else 5

    @property
    def minor(self) -> float:
        return self.major / self.subdivisions

    @property
    def label_decimals(self) -> int:
        """Decimals needed to print every major line value exactly."""
        return max(0, -self.exponent)


def choose_grid_step(pixels_per_unit: float) -> GridStep:
    """Pick the smallest 1/2/5 x 10^k step spanning at least ``MIN_MAJOR_SPACING_PX``."""
    if not math.isfinite(pixels_per_unit) or pixels_per_unit <= 0.0:
        raise ValueError(f"pixels_per_unit must be positive, got {pixels_per_unit!r}")
    minimum_step = MIN_MAJOR_SPACING_PX / pixels_per_unit
    exponent = math.floor(math.log10(minimum_step))
    for candidate_exponent in (exponent, exponent + 1):
        for mantissa in (1, 2, 5):
            step = GridStep(mantissa, candidate_exponent)
            # A tiny tolerance keeps exact boundaries from flipping on rounding.
            if step.major * (1.0 + 1e-9) >= minimum_step:
                return step
    raise AssertionError("unreachable: 10**(exponent + 1) always exceeds the minimum")


def format_coordinate(value: float, decimals: int) -> str:
    """Format ``value`` with ``decimals`` places, never producing ``-0``."""
    text = f"{value:.{decimals}f}"
    if text.startswith("-") and float(text) == 0.0:
        return text[1:]
    return text


@dataclass(frozen=True)
class AxisLabel:
    """Tick label of one major grid line, positioned along its axis."""

    position: float
    text: str


@dataclass(frozen=True)
class GridLayout:
    """Screen-space layout of the grid; positions are logical pixels.

    ``major_x`` / ``minor_x`` are x positions of vertical lines and ``major_y`` /
    ``minor_y`` are y positions of horizontal lines. The axes themselves are
    excluded from the major lines and located by ``origin_x`` / ``origin_y``,
    which may lie outside the viewport.
    """

    step: GridStep
    origin_x: float
    origin_y: float
    major_x: tuple[float, ...]
    major_y: tuple[float, ...]
    minor_x: tuple[float, ...]
    minor_y: tuple[float, ...]
    x_labels: tuple[AxisLabel, ...]
    y_labels: tuple[AxisLabel, ...]


@dataclass(frozen=True)
class Viewport2D:
    """A 2D camera observed through a viewport of ``width`` x ``height`` pixels."""

    camera: CameraState2D
    width: float
    height: float

    def __post_init__(self) -> None:
        for name in ("width", "height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be a non-negative finite number, got {value!r}")

    @property
    def pixels_per_unit(self) -> float:
        return BASE_PIXELS_PER_UNIT * clamp_zoom(self.camera.zoom)

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        scale = self.pixels_per_unit
        return (
            self.width / 2.0 + (x - self.camera.center_x) * scale,
            self.height / 2.0 - (y - self.camera.center_y) * scale,
        )

    def to_world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        scale = self.pixels_per_unit
        return (
            self.camera.center_x + (screen_x - self.width / 2.0) / scale,
            self.camera.center_y - (screen_y - self.height / 2.0) / scale,
        )

    def panned(self, delta_x: float, delta_y: float) -> CameraState2D:
        """Return the camera after dragging the content by a screen-space delta."""
        scale = self.pixels_per_unit
        return CameraState2D(
            center_x=self.camera.center_x - delta_x / scale,
            center_y=self.camera.center_y + delta_y / scale,
            zoom=self.camera.zoom,
        )

    def zoomed_at(self, screen_x: float, screen_y: float, factor: float) -> CameraState2D:
        """Return the camera zoomed by ``factor`` while keeping the anchor point fixed."""
        if not math.isfinite(factor) or factor <= 0.0:
            raise ValueError(f"zoom factor must be positive, got {factor!r}")
        anchor_x, anchor_y = self.to_world(screen_x, screen_y)
        zoom = clamp_zoom(clamp_zoom(self.camera.zoom) * factor)
        scale = BASE_PIXELS_PER_UNIT * zoom
        return CameraState2D(
            center_x=anchor_x - (screen_x - self.width / 2.0) / scale,
            center_y=anchor_y + (screen_y - self.height / 2.0) / scale,
            zoom=zoom,
        )

    def grid(self) -> GridLayout:
        """Lay out the grid lines and tick labels visible in the viewport."""
        step = choose_grid_step(self.pixels_per_unit)
        origin_x, origin_y = self.to_screen(0.0, 0.0)
        left, top = self.to_world(0.0, 0.0)
        right, bottom = self.to_world(self.width, self.height)
        major_x, minor_x, x_values = self._lines(step, left, right, axis=0)
        major_y, minor_y, y_values = self._lines(step, bottom, top, axis=1)
        return GridLayout(
            step=step,
            origin_x=origin_x,
            origin_y=origin_y,
            major_x=major_x,
            major_y=major_y,
            minor_x=minor_x,
            minor_y=minor_y,
            x_labels=tuple(
                AxisLabel(position, format_coordinate(value, step.label_decimals))
                for position, value in zip(major_x, x_values)
            ),
            y_labels=tuple(
                AxisLabel(position, format_coordinate(value, step.label_decimals))
                for position, value in zip(major_y, y_values)
            ),
        )

    def _lines(
        self, step: GridStep, low: float, high: float, *, axis: int
    ) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
        if self.width <= 0.0 or self.height <= 0.0:
            return (), (), ()
        minor = step.minor
        first = math.ceil(low / minor)
        last = math.floor(high / minor)
        if last - first + 1 > MAX_LINES_PER_AXIS * step.subdivisions:
            return (), (), ()
        major: list[float] = []
        minor_lines: list[float] = []
        values: list[float] = []
        for index in range(first, last + 1):
            # Integer multiples avoid accumulating floating-point drift.
            value = index * minor
            position = self.to_screen(value, 0.0)[0] if axis == 0 else self.to_screen(0.0, value)[1]
            if index % step.subdivisions:
                minor_lines.append(position)
            elif index != 0:
                major.append(position)
                values.append(index // step.subdivisions * step.major)
        return tuple(major), tuple(minor_lines), tuple(values)


def distance_to_segment(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    """Euclidean distance from ``point`` to the segment ``start``–``end``."""
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_squared))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def snap_to_step(value: float, step: float) -> float:
    """Round ``value`` to the nearest multiple of ``step`` without float noise."""
    return round(round(value / step) * step, 12) + 0.0
