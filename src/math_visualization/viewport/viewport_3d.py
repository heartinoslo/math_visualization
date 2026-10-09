"""Pure 3D viewport mathematics: orbit camera, projection, picking and grid layout.

Mathematical space is right-handed with ``z`` up; the active plane is ``z = 0``.
Qt Quick 3D scene space is right-handed with ``Y`` up, so a mathematical point
``(x, y, z)`` maps to the scene point ``(x, z, -y) * SCENE_UNITS_PER_MATH_UNIT``.
That mapping is a proper rotation plus uniform scale, so orientation and
handedness are preserved.

Camera angles are in degrees. The azimuth is measured in the XY plane from
``+x`` towards ``+y``; the elevation is measured from the XY plane towards ``+z``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from math_visualization.scene.workspace_state import CameraState3D, ProjectionMode
from math_visualization.viewport.viewport_2d import GridStep, choose_grid_step


Vector3 = tuple[float, float, float]

SCENE_UNITS_PER_MATH_UNIT = 100.0
FIELD_OF_VIEW_DEGREES = 45.0
MIN_DISTANCE = 0.5
MAX_DISTANCE = 500.0
MAX_ELEVATION = 89.0
ORBIT_DEGREES_PER_PIXEL = 0.3
ZOOM_FACTOR_PER_NOTCH = 1.15
WHEEL_NOTCH = 120.0
# The grid spans this many major steps on each side of its centre.
GRID_HALF_EXTENT_MAJORS = 10
# Axes are drawn as a gizmo whose length follows the camera distance, so they
# change continuously while zooming and never reach the eye.
AXIS_HALF_LENGTH_PER_DISTANCE = 0.34
AUXILIARY_HALF_EXTENT_MAJORS = 4

CAMERA_PRESETS: dict[str, tuple[float, float]] = {
    "front": (-90.0, 0.0),
    "top": (-90.0, MAX_ELEVATION),
    "oblique": (-60.0, 25.0),
}


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vector3, factor: float) -> Vector3:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalized(a: Vector3) -> Vector3:
    return _scale(a, 1.0 / math.sqrt(_dot(a, a)))


def math_to_scene(point: Vector3) -> Vector3:
    """Map a mathematical point to Qt Quick 3D scene coordinates."""
    x, y, z = point
    s = SCENE_UNITS_PER_MATH_UNIT
    return (x * s, z * s, -y * s)


def _wrap_degrees(angle: float) -> float:
    """Wrap ``angle`` into ``(-180, 180]``."""
    wrapped = math.fmod(angle + 180.0, 360.0)
    if wrapped <= 0.0:
        wrapped += 360.0
    return wrapped - 180.0


def _quaternion_from_basis(right: Vector3, up: Vector3, back: Vector3) -> tuple[float, float, float, float]:
    """Return ``(w, x, y, z)`` for the rotation whose matrix columns are the given axes."""
    m00, m10, m20 = right
    m01, m11, m21 = up
    m02, m12, m22 = back
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        return (0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s)
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        return ((m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s)
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        return ((m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s)
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
    return ((m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s)


@dataclass(frozen=True)
class Projection:
    """Screen position of a projected point; ``visible`` is false behind the camera."""

    x: float
    y: float
    visible: bool


@dataclass(frozen=True)
class Grid3D:
    """Layout of the active-plane grid, centred on a major line near the target."""

    step: GridStep
    center_x: float
    center_y: float
    half_extent: float


@dataclass(frozen=True)
class Viewport3D:
    """An orbit camera observed through a viewport of ``width`` x ``height`` pixels."""

    camera: CameraState3D
    width: float
    height: float

    def __post_init__(self) -> None:
        for name in ("width", "height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be a non-negative finite number, got {value!r}")

    # Camera frame -------------------------------------------------------

    @property
    def target(self) -> Vector3:
        camera = self.camera
        return (camera.target_x, camera.target_y, camera.target_z)

    @property
    def distance(self) -> float:
        return min(max(self.camera.distance, MIN_DISTANCE), MAX_DISTANCE)

    @property
    def elevation(self) -> float:
        return min(max(self.camera.elevation, -MAX_ELEVATION), MAX_ELEVATION)

    @property
    def backward(self) -> Vector3:
        """Unit vector from the target towards the eye."""
        azimuth = math.radians(self.camera.azimuth)
        elevation = math.radians(self.elevation)
        return (
            math.cos(elevation) * math.cos(azimuth),
            math.cos(elevation) * math.sin(azimuth),
            math.sin(elevation),
        )

    @property
    def forward(self) -> Vector3:
        return _scale(self.backward, -1.0)

    @property
    def right(self) -> Vector3:
        return _normalized(_cross(self.forward, (0.0, 0.0, 1.0)))

    @property
    def up(self) -> Vector3:
        return _cross(self.right, self.forward)

    @property
    def eye(self) -> Vector3:
        return _add(self.target, _scale(self.backward, self.distance))

    @property
    def axis_half_length(self) -> float:
        return self.distance * AXIS_HALF_LENGTH_PER_DISTANCE

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height > 0.0 else 1.0

    @property
    def visible_height(self) -> float:
        """Height of the view, in math units, at the target's depth."""
        return 2.0 * self.distance * math.tan(math.radians(FIELD_OF_VIEW_DEGREES) / 2.0)

    # Scene-space camera -------------------------------------------------

    @property
    def scene_position(self) -> Vector3:
        return math_to_scene(self.eye)

    @property
    def scene_rotation(self) -> tuple[float, float, float, float]:
        """Scene rotation ``(w, x, y, z)``; Qt cameras look along local ``-Z``."""
        right = _normalized(math_to_scene(self.right))
        up = _normalized(math_to_scene(self.up))
        back = _normalized(math_to_scene(self.backward))
        return _quaternion_from_basis(right, up, back)

    @property
    def clip_near(self) -> float:
        return self.distance * 0.01 * SCENE_UNITS_PER_MATH_UNIT

    @property
    def clip_far(self) -> float:
        return self.distance * 100.0 * SCENE_UNITS_PER_MATH_UNIT

    @property
    def orthographic_magnification(self) -> float:
        """Pixels per scene unit that matches the perspective scale at the target."""
        if self.height <= 0.0:
            return 1.0
        return self.height / (self.visible_height * SCENE_UNITS_PER_MATH_UNIT)

    # Interaction --------------------------------------------------------

    def orbited(self, delta_x: float, delta_y: float) -> CameraState3D:
        """Rotate around the target by a screen-space drag."""
        return replace(
            self.camera,
            azimuth=_wrap_degrees(self.camera.azimuth - delta_x * ORBIT_DEGREES_PER_PIXEL),
            elevation=min(
                max(self.elevation + delta_y * ORBIT_DEGREES_PER_PIXEL, -MAX_ELEVATION),
                MAX_ELEVATION,
            ),
        )

    def panned(self, delta_x: float, delta_y: float) -> CameraState3D:
        """Move the target so content at the target's depth follows the pointer."""
        if self.height <= 0.0:
            return self.camera
        units_per_pixel = self.visible_height / self.height
        offset = _add(
            _scale(self.right, -delta_x * units_per_pixel),
            _scale(self.up, delta_y * units_per_pixel),
        )
        x, y, z = _add(self.target, offset)
        return replace(self.camera, target_x=x, target_y=y, target_z=z)

    def zoomed(self, wheel_delta: float) -> CameraState3D:
        """Move towards the target for positive wheel deltas, clamped to the limits."""
        factor = ZOOM_FACTOR_PER_NOTCH ** (wheel_delta / WHEEL_NOTCH)
        distance = min(max(self.distance / factor, MIN_DISTANCE), MAX_DISTANCE)
        return replace(self.camera, distance=distance)

    def with_preset(self, name: str) -> CameraState3D:
        """Apply a named view direction, keeping target, distance and projection."""
        try:
            azimuth, elevation = CAMERA_PRESETS[name]
        except KeyError:
            raise ValueError(f"Unknown camera preset: {name!r}") from None
        return replace(self.camera, azimuth=azimuth, elevation=elevation)

    # Projection and picking ---------------------------------------------

    def project(self, point: Vector3) -> Projection:
        """Project a mathematical point to screen coordinates."""
        relative = _add(point, _scale(self.eye, -1.0))
        depth = _dot(relative, self.forward)
        half_height = self.visible_height / 2.0
        if self.camera.projection_mode is ProjectionMode.PERSPECTIVE:
            if depth <= self.clip_near / SCENE_UNITS_PER_MATH_UNIT:
                return Projection(0.0, 0.0, False)
            half_height *= depth / self.distance
        ndc_x = _dot(relative, self.right) / (half_height * self.aspect)
        ndc_y = _dot(relative, self.up) / half_height
        return Projection(
            (ndc_x + 1.0) / 2.0 * self.width,
            (1.0 - ndc_y) / 2.0 * self.height,
            True,
        )

    def units_per_pixel(self, point: Vector3) -> float:
        """Mathematical length covered by one screen pixel at ``point``.

        Orthographic views are uniform; in perspective the footprint grows with
        the depth along the view direction (clamped to the near plane).
        """
        if self.height <= 0.0:
            return 0.0
        units = self.visible_height / self.height
        if self.camera.projection_mode is ProjectionMode.PERSPECTIVE:
            depth = _dot(_add(point, _scale(self.eye, -1.0)), self.forward)
            units *= max(depth, self.clip_near / SCENE_UNITS_PER_MATH_UNIT) / self.distance
        return units

    def ray(self, screen_x: float, screen_y: float) -> tuple[Vector3, Vector3]:
        """Return the origin and unit direction of the ray through a screen point."""
        ndc_x = 2.0 * screen_x / self.width - 1.0 if self.width > 0.0 else 0.0
        ndc_y = 1.0 - 2.0 * screen_y / self.height if self.height > 0.0 else 0.0
        half_height = self.visible_height / 2.0
        offset = _add(
            _scale(self.right, ndc_x * half_height * self.aspect),
            _scale(self.up, ndc_y * half_height),
        )
        if self.camera.projection_mode is ProjectionMode.PERSPECTIVE:
            direction = _normalized(_add(_scale(self.forward, self.distance), offset))
            return self.eye, direction
        return _add(self.eye, offset), self.forward

    def pick_active_plane(self, screen_x: float, screen_y: float) -> tuple[float, float] | None:
        """Intersect the pointer ray with the active ``z = 0`` plane."""
        origin, direction = self.ray(screen_x, screen_y)
        if abs(direction[2]) < 1e-9:
            return None
        distance = -origin[2] / direction[2]
        if distance <= 0.0:
            return None
        point = _add(origin, _scale(direction, distance))
        return point[0], point[1]

    # Grid -----------------------------------------------------------------

    def grid(self) -> Grid3D:
        """Choose the active-plane grid spacing from the scale at the target."""
        pixels_per_unit = self.height / self.visible_height if self.height > 0.0 else 1.0
        step = choose_grid_step(pixels_per_unit)
        return Grid3D(
            step=step,
            center_x=round(self.camera.target_x / step.major) * step.major,
            center_y=round(self.camera.target_y / step.major) * step.major,
            half_extent=step.major * GRID_HALF_EXTENT_MAJORS,
        )


def grid_positions(center: float, half_extent: float, step: float, skip_zero: bool = True) -> list[float]:
    """Positions ``center + k * step`` within ``half_extent``, optionally omitting 0."""
    count = round(half_extent / step)
    first = round(center / step) - count
    positions = [(first + index) * step for index in range(2 * count + 1)]
    return [p for p in positions if not (skip_zero and abs(p) < step * 1e-6)]


def plane_segments(
    plane: str,
    center: tuple[float, float],
    half_extent: float,
    step: float,
    *,
    skip_every: int = 0,
) -> list[tuple[Vector3, Vector3]]:
    """Grid segments in a coordinate plane (``"xy"``, ``"xz"`` or ``"yz"``).

    ``center`` holds the plane's two in-plane coordinates in axis order. When
    ``skip_every`` is set, lines at multiples of ``skip_every * step`` (the major
    lines) are left out so minor and major grids never overlap. Lines on the
    axes themselves are always omitted.
    """
    axes = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}[plane]

    def keep(position: float) -> bool:
        if not skip_every:
            return True
        ratio = position / (step * skip_every)
        return abs(ratio - round(ratio)) > 1e-6

    segments: list[tuple[Vector3, Vector3]] = []
    for line_axis, other_axis in (axes, axes[::-1]):
        line_center = center[axes.index(line_axis)]
        other_center = center[axes.index(other_axis)]
        for position in grid_positions(line_center, half_extent, step):
            if not keep(position):
                continue
            start = [0.0, 0.0, 0.0]
            end = [0.0, 0.0, 0.0]
            start[line_axis] = end[line_axis] = position
            start[other_axis] = other_center - half_extent
            end[other_axis] = other_center + half_extent
            segments.append((tuple(start), tuple(end)))
    return segments
