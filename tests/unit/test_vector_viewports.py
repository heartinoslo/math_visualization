"""Tests for vector drawing data, picking and dragging in both viewports."""

import math

import pytest
from PySide6.QtGui import QVector3D

from math_visualization.math_core import Vector2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel
from math_visualization.viewport.viewport_2d import distance_to_segment, snap_to_step
from math_visualization.viewport.viewport_3d import SCENE_UNITS_PER_MATH_UNIT, math_to_scene


def make_app(vectors=((2.0, 1.0),)):
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    view_model.viewport2D.setViewportSize(800.0, 600.0)
    view_model.viewport3D.setViewportSize(900.0, 600.0)
    ids = []
    for x, y in vectors:
        identifier = view_model.scene.addVector()
        view_model.scene.setComponents(identifier, x, y)
        ids.append(identifier)
    return document, view_model, ids


def test_segment_distance_and_snapping_helpers() -> None:
    assert distance_to_segment((5, 5), (0, 0), (10, 0)) == 5
    assert distance_to_segment((-3, 4), (0, 0), (10, 0)) == 5
    assert distance_to_segment((1, 1), (0, 0), (0, 0)) == math.sqrt(2)
    assert snap_to_step(0.29999, 0.1) == 0.3
    assert snap_to_step(-0.04, 0.2) == 0.0


def test_2d_shapes_place_the_tip_in_screen_space() -> None:
    _, view_model, ids = make_app()
    shape = view_model.viewport2D.vectorShapes[0]

    assert (shape["tipX"], shape["tipY"]) == (400 + 2 * 80, 300 - 1 * 80)
    assert shape["selected"] and not shape["isZero"] and shape["objectId"] == ids[0]


def test_2d_hit_test_prefers_tips_then_shafts() -> None:
    _, view_model, ids = make_app()
    viewport = view_model.viewport2D

    assert viewport.hitTest(565, 215) == {"objectId": ids[0], "part": "tip"}
    assert viewport.hitTest(480, 262) == {"objectId": ids[0], "part": "shaft"}
    assert viewport.hitTest(100, 100) == {"objectId": "", "part": ""}


def test_2d_drag_keeps_the_grab_offset_and_merges_into_one_undo_step() -> None:
    document, view_model, ids = make_app()
    viewport = view_model.viewport2D
    history = view_model.scene.commands.undo_count

    assert viewport.beginVectorDrag(565, 215) == "tip"
    viewport.dragVector(565 + 40, 215, False)
    viewport.dragVector(565 + 80, 215 - 40, False)
    viewport.endVectorDrag()

    assert document.vectors[0].vector == Vector2(3, 1.5)
    assert view_model.scene.commands.undo_count == history + 1


def test_2d_drag_snaps_to_the_minor_grid() -> None:
    document, view_model, _ = make_app()
    viewport = view_model.viewport2D

    viewport.beginVectorDrag(560, 220)
    viewport.dragVector(560 + 13, 220 - 7, True)
    viewport.endVectorDrag()

    assert document.vectors[0].vector == Vector2(2.2, 1.0)


def test_2d_shaft_press_selects_without_dragging() -> None:
    document, view_model, ids = make_app([(2.0, 1.0), (-1.0, 2.0)])
    viewport = view_model.viewport2D

    assert viewport.beginVectorDrag(480, 262) == "shaft"
    viewport.dragVector(700, 100, False)

    assert view_model.scene.selectedId == ids[0]
    assert document.vectors[0].vector == Vector2(2, 1)


def test_3d_embeds_vectors_in_the_xy_plane() -> None:
    _, view_model, _ = make_app()
    arrow = view_model.viewport3D.vectorArrows[0]

    direction = arrow["rotation"].rotatedVector(QVector3D(0.0, 1.0, 0.0))
    expected = math_to_scene((2.0, 1.0, 0.0))
    norm = math.hypot(*expected)

    assert expected == (200.0, 0.0, -100.0)
    assert (direction.x(), direction.y(), direction.z()) == pytest.approx(
        tuple(c / norm for c in expected), abs=1e-5
    )
    total = arrow["shaftLength"] + arrow["headLength"]
    assert total == pytest.approx(math.hypot(2, 1) * SCENE_UNITS_PER_MATH_UNIT)


def test_3d_short_vectors_shrink_their_head_and_zero_vectors_are_flagged() -> None:
    _, view_model, _ = make_app([(0.05, 0.0), (0.0, 0.0)])
    short, zero = view_model.viewport3D.vectorArrows

    assert short["headLength"] == pytest.approx(0.5 * 0.05 * SCENE_UNITS_PER_MATH_UNIT)
    assert short["shaftLength"] > 0
    assert zero["isZero"] and not short["isZero"]


def test_3d_labels_and_component_lines_follow_the_selection() -> None:
    _, view_model, ids = make_app([(2.0, 1.0), (-1.0, 3.0)])
    viewport = view_model.viewport3D

    names = [label["name"] for label in viewport.vectorLabels]
    assert names == ["u", "v"]
    assert viewport.componentLinesVisible
    assert viewport.componentLinesGeometry.vertex_count == 4
    view_model.scene.clearSelection()
    assert not viewport.componentLinesVisible
    assert viewport.componentLinesGeometry.vertex_count == 0


@pytest.mark.parametrize(
    ("azimuth", "elevation", "projection"),
    [(-60.0, 25.0, "perspective"), (30.0, 70.0, "perspective"), (-150.0, 10.0, "orthographic"), (-90.0, 89.0, "perspective")],
)
def test_3d_drag_from_any_angle_keeps_the_tip_under_the_pointer_in_the_plane(
    azimuth, elevation, projection
) -> None:
    document, view_model, _ = make_app()
    viewport = view_model.viewport3D
    view_model.workspace.setCamera3D(0.0, 0.0, 0.0, azimuth, elevation, 12.0)
    view_model.workspace.setProjectionMode3D(projection)
    tip = viewport.viewport().project((2.0, 1.0, 0.0))

    assert viewport.beginVectorDrag(tip.x, tip.y) == "tip"
    target = viewport.viewport().project((-1.5, 2.5, 0.0))
    viewport.dragVector(target.x, target.y, False)
    viewport.endVectorDrag()

    moved = document.vectors[0].vector
    assert (moved.x, moved.y) == pytest.approx((-1.5, 2.5), abs=1e-6)


def test_3d_grab_offset_is_kept_in_plane_coordinates() -> None:
    document, view_model, _ = make_app()
    viewport = view_model.viewport3D
    tip = viewport.viewport().project((2.0, 1.0, 0.0))
    press = (tip.x + 4, tip.y - 3)
    pressed_on_plane = viewport.viewport().pick_active_plane(*press)

    viewport.beginVectorDrag(*press)
    viewport.dragVector(300.0, 350.0, False)
    viewport.endVectorDrag()

    pointer_on_plane = viewport.viewport().pick_active_plane(300.0, 350.0)
    moved = document.vectors[0].vector
    assert (moved.x - pointer_on_plane[0], moved.y - pointer_on_plane[1]) == pytest.approx(
        (2.0 - pressed_on_plane[0], 1.0 - pressed_on_plane[1])
    )


def test_3d_hit_test_and_empty_space() -> None:
    _, view_model, ids = make_app()
    viewport = view_model.viewport3D
    tip = viewport.viewport().project((2.0, 1.0, 0.0))
    middle = viewport.viewport().project((1.0, 0.5, 0.0))

    assert viewport.hitTest(tip.x, tip.y) == {"objectId": ids[0], "part": "tip"}
    assert viewport.hitTest(middle.x, middle.y) == {"objectId": ids[0], "part": "shaft"}
    assert viewport.hitTest(5.0, 5.0)["part"] == ""


def test_2d_and_3d_read_the_same_vector() -> None:
    document, view_model, ids = make_app()
    view_model.scene.setComponents(ids[0], -3.0, 0.5)

    shape = view_model.viewport2D.vectorShapes[0]
    label = view_model.viewport3D.vectorLabels[0]
    tip_3d = view_model.viewport3D.viewport().project((-3.0, 0.5, 0.0))

    assert (shape["tipX"], shape["tipY"]) == (400 - 3 * 80, 300 - 0.5 * 80)
    assert (label["x"], label["y"]) == pytest.approx((tip_3d.x, tip_3d.y))
