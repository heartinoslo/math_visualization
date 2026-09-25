"""Tests for renderer-independent 2D viewport mathematics."""

import math

import pytest

from math_visualization.scene.workspace_state import CameraState2D
from math_visualization.viewport.viewport_2d import (
    BASE_PIXELS_PER_UNIT,
    MAX_ZOOM,
    MIN_MAJOR_SPACING_PX,
    MIN_ZOOM,
    GridStep,
    Viewport2D,
    choose_grid_step,
    format_coordinate,
)


TOLERANCE = 1e-9


def viewport(center_x=0.0, center_y=0.0, zoom=1.0, width=800.0, height=600.0) -> Viewport2D:
    return Viewport2D(CameraState2D(center_x, center_y, zoom), width, height)


def test_origin_is_drawn_at_viewport_centre_with_y_up() -> None:
    view = viewport()

    assert view.to_screen(0.0, 0.0) == (400.0, 300.0)
    assert view.to_screen(1.0, 1.0) == (400.0 + BASE_PIXELS_PER_UNIT, 300.0 - BASE_PIXELS_PER_UNIT)


@pytest.mark.parametrize(
    "camera",
    [(0.0, 0.0, 1.0), (12.5, -3.25, 0.37), (-1e4, 2e4, 250.0), (0.1, 0.2, MIN_ZOOM)],
)
@pytest.mark.parametrize("point", [(0.0, 0.0), (1.5, -2.5), (-123.456, 789.01)])
def test_screen_world_round_trip(camera, point) -> None:
    view = viewport(*camera)

    x, y = view.to_world(*view.to_screen(*point))

    assert math.isclose(x, point[0], rel_tol=TOLERANCE, abs_tol=TOLERANCE)
    assert math.isclose(y, point[1], rel_tol=TOLERANCE, abs_tol=TOLERANCE)


def test_pan_moves_content_with_the_pointer() -> None:
    view = viewport(zoom=2.0)
    before = view.to_screen(1.0, 1.0)

    panned = Viewport2D(view.panned(30.0, -20.0), view.width, view.height)
    after = panned.to_screen(1.0, 1.0)

    assert math.isclose(after[0], before[0] + 30.0)
    assert math.isclose(after[1], before[1] - 20.0)
    assert panned.camera.zoom == 2.0


@pytest.mark.parametrize("factor", [1.15, 0.5, 8.0])
@pytest.mark.parametrize("anchor", [(400.0, 300.0), (10.0, 590.0), (777.0, 3.0)])
def test_zoom_keeps_anchor_point_fixed(factor, anchor) -> None:
    view = viewport(center_x=3.0, center_y=-1.0, zoom=1.7)
    anchor_world = view.to_world(*anchor)

    zoomed = Viewport2D(view.zoomed_at(*anchor, factor), view.width, view.height)

    assert math.isclose(zoomed.camera.zoom, 1.7 * factor)
    screen = zoomed.to_screen(*anchor_world)
    assert math.isclose(screen[0], anchor[0], abs_tol=1e-7)
    assert math.isclose(screen[1], anchor[1], abs_tol=1e-7)


def test_zoom_is_clamped_without_moving_the_anchor() -> None:
    view = viewport(zoom=MAX_ZOOM / 2)
    anchor = (100.0, 100.0)
    anchor_world = view.to_world(*anchor)

    zoomed = Viewport2D(view.zoomed_at(*anchor, 10.0), view.width, view.height)

    assert zoomed.camera.zoom == MAX_ZOOM
    screen = zoomed.to_screen(*anchor_world)
    assert math.isclose(screen[0], anchor[0], abs_tol=1e-6)
    assert math.isclose(screen[1], anchor[1], abs_tol=1e-6)
    assert viewport(zoom=MIN_ZOOM).zoomed_at(0.0, 0.0, 0.1).zoom == MIN_ZOOM


def test_zoom_rejects_invalid_factor() -> None:
    with pytest.raises(ValueError):
        viewport().zoomed_at(0.0, 0.0, 0.0)


@pytest.mark.parametrize(
    ("pixels_per_unit", "expected"),
    [(80.0, GridStep(1, 0)), (40.0, GridStep(2, 0)), (20.0, GridStep(5, 0)), (800.0, GridStep(1, -1))],
)
def test_grid_step_selection(pixels_per_unit, expected) -> None:
    assert choose_grid_step(pixels_per_unit) == expected


def test_grid_step_is_stable_and_bounded_across_continuous_zoom() -> None:
    previous = None
    for index in range(-3000, 3001):
        zoom = 10.0 ** (index / 1000)
        step = choose_grid_step(BASE_PIXELS_PER_UNIT * zoom)
        spacing = step.major * BASE_PIXELS_PER_UNIT * zoom
        assert step.mantissa in (1, 2, 5)
        assert MIN_MAJOR_SPACING_PX * (1 - 1e-9) <= spacing < MIN_MAJOR_SPACING_PX * 2.5 + 1e-6
        if previous is not None:
            # Zooming in never makes the major spacing coarser.
            assert step.major <= previous.major
        previous = step


def test_grid_lines_are_multiples_of_the_step_and_exclude_axes() -> None:
    view = viewport(center_x=0.3, center_y=-0.2)
    grid = view.grid()

    assert grid.step == GridStep(1, 0)
    assert grid.origin_x not in grid.major_x
    for position in grid.major_x:
        x, _ = view.to_world(position, 0.0)
        assert math.isclose(x, round(x), abs_tol=1e-9)
    for position in grid.major_x + grid.minor_x:
        assert 0.0 <= position <= view.width
    for position in grid.major_y + grid.minor_y:
        assert 0.0 <= position <= view.height
    assert not set(grid.major_x) & set(grid.minor_x)


def test_grid_labels_follow_major_lines() -> None:
    view = viewport(zoom=0.5)
    grid = view.grid()

    assert [label.position for label in grid.x_labels] == list(grid.major_x)
    assert "2" in [label.text for label in grid.x_labels]
    assert "-2" in [label.text for label in grid.y_labels]


def test_fractional_steps_produce_clean_labels() -> None:
    grid = viewport(zoom=20.0).grid()

    assert grid.step == GridStep(5, -2)
    texts = [label.text for label in grid.x_labels]
    assert "0.05" in texts
    assert all(len(text.split(".")[1]) == 2 for text in texts)


def test_empty_viewport_has_no_lines() -> None:
    grid = viewport(width=0.0, height=0.0).grid()

    assert grid.major_x == grid.minor_y == ()


def test_line_count_stays_bounded() -> None:
    grid = viewport(width=3840.0, height=2160.0).grid()

    assert len(grid.major_x) + len(grid.minor_x) <= 3840.0 / (MIN_MAJOR_SPACING_PX / 5) + 2


@pytest.mark.parametrize(
    ("value", "decimals", "expected"),
    [(0.0, 1, "0.0"), (-0.00001, 2, "0.00"), (-1.25, 1, "-1.2"), (2.0, 0, "2")],
)
def test_format_coordinate(value, decimals, expected) -> None:
    assert format_coordinate(value, decimals) == expected


def test_viewport_rejects_invalid_size() -> None:
    with pytest.raises(ValueError):
        viewport(width=-1.0)
