"""Tests for renderer-independent 3D viewport mathematics."""

import math

import pytest
from PySide6.QtGui import QQuaternion, QVector3D

from math_visualization.scene.workspace_state import CameraState3D, ProjectionMode
from math_visualization.viewport.viewport_3d import (
    CAMERA_PRESETS,
    MAX_DISTANCE,
    MAX_ELEVATION,
    MIN_DISTANCE,
    SCENE_UNITS_PER_MATH_UNIT,
    Viewport3D,
    grid_positions,
    math_to_scene,
    plane_segments,
)


def close(a, b, tolerance=1e-7) -> bool:
    return all(math.isclose(x, y, abs_tol=tolerance) for x, y in zip(a, b))


def viewport(width=900.0, height=600.0, **camera) -> Viewport3D:
    return Viewport3D(CameraState3D(**camera), width, height)


ANGLES = [(-60.0, 25.0), (0.0, 0.0), (135.0, -40.0), (-90.0, MAX_ELEVATION), (179.0, 60.0)]


def test_math_to_scene_is_a_proper_rotation_with_z_up() -> None:
    s = SCENE_UNITS_PER_MATH_UNIT
    x, y, z = (math_to_scene(axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))

    assert (x, y, z) == ((s, 0, 0), (0, 0, -s), (0, s, 0))
    cross = QVector3D.crossProduct(QVector3D(*x), QVector3D(*y))
    assert close((cross.x(), cross.y(), cross.z()), (0, s * s, 0))


def test_front_view_looks_along_plus_y_with_x_right_and_z_up() -> None:
    view = viewport(azimuth=-90.0, elevation=0.0, distance=10.0)

    assert close(view.eye, (0.0, -10.0, 0.0))
    assert close(view.forward, (0.0, 1.0, 0.0))
    assert close(view.right, (1.0, 0.0, 0.0))
    assert close(view.up, (0.0, 0.0, 1.0))


@pytest.mark.parametrize(("azimuth", "elevation"), ANGLES)
def test_camera_basis_is_orthonormal(azimuth, elevation) -> None:
    view = viewport(azimuth=azimuth, elevation=elevation)
    vectors = (view.right, view.up, view.forward)

    for first in vectors:
        assert math.isclose(sum(c * c for c in first), 1.0)
        for second in vectors:
            if first is not second:
                assert abs(sum(a * b for a, b in zip(first, second))) < 1e-9


@pytest.mark.parametrize(("azimuth", "elevation"), ANGLES)
def test_scene_rotation_maps_local_axes_to_camera_basis(azimuth, elevation) -> None:
    view = viewport(azimuth=azimuth, elevation=elevation)
    rotation = QQuaternion(*view.scene_rotation)

    for local, expected in (
        ((1, 0, 0), view.right),
        ((0, 1, 0), view.up),
        ((0, 0, -1), view.forward),
    ):
        rotated = rotation.rotatedVector(QVector3D(*local))
        scene = math_to_scene(expected)
        assert close(
            (rotated.x(), rotated.y(), rotated.z()),
            tuple(c / SCENE_UNITS_PER_MATH_UNIT for c in scene),
            1e-5,
        )


@pytest.mark.parametrize("projection", list(ProjectionMode))
def test_target_projects_to_viewport_centre(projection) -> None:
    view = viewport(target_x=2.0, target_y=-1.0, target_z=0.5, projection_mode=projection)

    point = view.project(view.target)

    assert point.visible
    assert close((point.x, point.y), (450.0, 300.0))


@pytest.mark.parametrize("projection", list(ProjectionMode))
@pytest.mark.parametrize(("azimuth", "elevation"), [(-60.0, 25.0), (30.0, 70.0), (-150.0, -35.0)])
def test_picking_inverts_projection_on_the_active_plane(projection, azimuth, elevation) -> None:
    view = viewport(azimuth=azimuth, elevation=elevation, projection_mode=projection)

    for point in ((0.0, 0.0), (1.5, -2.0), (-3.0, 0.25)):
        screen = view.project((point[0], point[1], 0.0))
        picked = view.pick_active_plane(screen.x, screen.y)
        assert picked is not None
        assert close(picked, point, 1e-6)


def test_picking_misses_when_the_ray_leaves_the_plane() -> None:
    view = viewport(azimuth=-90.0, elevation=10.0)

    assert view.pick_active_plane(450.0, 0.0) is None
    assert viewport(azimuth=-90.0, elevation=0.0).pick_active_plane(450.0, 300.0) is None


def test_points_behind_the_camera_are_not_visible() -> None:
    view = viewport(azimuth=-90.0, elevation=0.0, distance=5.0)

    assert not view.project((0.0, -20.0, 0.0)).visible


def test_orbit_changes_only_angles_and_clamps_elevation() -> None:
    view = viewport(target_x=1.0, azimuth=170.0, elevation=80.0, distance=7.0)

    camera = view.orbited(-50.0, 100.0)

    assert camera.azimuth == pytest.approx(-175.0)
    assert camera.elevation == MAX_ELEVATION
    assert (camera.target_x, camera.distance) == (1.0, 7.0)


@pytest.mark.parametrize("projection", list(ProjectionMode))
def test_pan_moves_target_depth_content_with_the_pointer(projection) -> None:
    view = viewport(azimuth=-30.0, elevation=40.0, projection_mode=projection)
    anchor = view.target

    moved = Viewport3D(view.panned(60.0, -25.0), view.width, view.height)
    screen = moved.project(anchor)

    assert close((screen.x, screen.y), (450.0 + 60.0, 300.0 - 25.0), 1e-6)
    assert moved.camera.distance == view.camera.distance


def test_zoom_scales_distance_and_respects_limits() -> None:
    view = viewport(distance=10.0)

    assert view.zoomed(240.0).distance == pytest.approx(10.0 / 1.15**2)
    assert viewport(distance=MIN_DISTANCE).zoomed(1200.0).distance == MIN_DISTANCE
    assert viewport(distance=MAX_DISTANCE).zoomed(-1200.0).distance == MAX_DISTANCE


def test_presets_keep_target_distance_and_projection() -> None:
    view = viewport(target_x=3.0, distance=6.0, projection_mode="orthographic")

    for name, (azimuth, elevation) in CAMERA_PRESETS.items():
        camera = view.with_preset(name)
        assert (camera.azimuth, camera.elevation) == (azimuth, elevation)
        assert (camera.target_x, camera.distance) == (3.0, 6.0)
        assert camera.projection_mode is ProjectionMode.ORTHOGRAPHIC
    with pytest.raises(ValueError):
        view.with_preset("isometric")


def test_default_camera_is_the_oblique_preset() -> None:
    camera = CameraState3D()

    assert (camera.azimuth, camera.elevation) == CAMERA_PRESETS["oblique"]


def test_orthographic_scale_matches_perspective_at_the_target() -> None:
    view = viewport(distance=9.0)

    visible_scene_height = view.height / view.orthographic_magnification

    assert visible_scene_height == pytest.approx(view.visible_height * SCENE_UNITS_PER_MATH_UNIT)


def test_grid_is_centred_on_a_major_line_near_the_target() -> None:
    grid = viewport(target_x=7.3, target_y=-2.6).grid()

    assert grid.center_x / grid.step.major == pytest.approx(round(grid.center_x / grid.step.major))
    assert abs(grid.center_x - 7.3) <= grid.step.major / 2
    assert abs(grid.center_y + 2.6) <= grid.step.major / 2


def test_grid_positions_skip_the_axis() -> None:
    assert grid_positions(0.0, 2.0, 1.0) == [-2.0, -1.0, 1.0, 2.0]
    assert grid_positions(10.0, 1.0, 1.0) == [9.0, 10.0, 11.0]


def test_plane_segments_lie_in_their_plane_and_skip_major_lines() -> None:
    minor = plane_segments("xy", (0.0, 0.0), 2.0, 0.5, skip_every=2)
    major = plane_segments("xy", (0.0, 0.0), 2.0, 1.0)
    vertical = plane_segments("xz", (0.0, 0.0), 1.0, 1.0)

    assert all(start[2] == end[2] == 0.0 for start, end in minor + major)
    assert all(start[1] == end[1] == 0.0 for start, end in vertical)
    # Minor lines at 0.5 intervals, excluding multiples of 1.0 (majors) and 0 (axes).
    assert sorted({start[0] for start, end in minor if start[0] == end[0]}) == [-1.5, -0.5, 0.5, 1.5]
    assert len(major) == 8


@pytest.mark.parametrize("projection", list(ProjectionMode))
@pytest.mark.parametrize("point", [(0.0, 0.0, 0.0), (4.0, -3.0, 0.0), (-6.0, 5.0, 2.0)])
def test_units_per_pixel_spans_one_pixel_at_the_point(projection, point) -> None:
    view = viewport(projection_mode=projection)
    units = view.units_per_pixel(point)
    shifted = tuple(p + units * r for p, r in zip(point, view.right))

    a, b = view.project(point), view.project(shifted)

    assert math.hypot(b.x - a.x, b.y - a.y) == pytest.approx(1.0, rel=1e-6)


def test_units_per_pixel_grows_with_depth_only_in_perspective() -> None:
    near, far = (0.0, 0.0, 0.0), (8.0, 8.0, 0.0)
    perspective = viewport(projection_mode=ProjectionMode.PERSPECTIVE)
    orthographic = viewport(projection_mode=ProjectionMode.ORTHOGRAPHIC)

    assert perspective.units_per_pixel(far) > perspective.units_per_pixel(near)
    assert orthographic.units_per_pixel(far) == orthographic.units_per_pixel(near)
    assert perspective.units_per_pixel(near) == pytest.approx(perspective.visible_height / 600.0)
