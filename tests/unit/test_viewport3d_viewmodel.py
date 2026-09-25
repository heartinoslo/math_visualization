"""Tests for the 3D viewport view model."""

import math

import pytest

from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import CameraState2D, CameraState3D
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel
from math_visualization.viewmodels.viewport3d_viewmodel import MIN_TICK_LABEL_SPACING_PX


def make_view_model():
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    viewport = view_model.viewport3D
    viewport.setViewportSize(900.0, 600.0)
    return document, view_model, viewport


def record(signal) -> list:
    emissions: list = []
    signal.connect(lambda *arguments: emissions.append(arguments))
    return emissions


def test_grids_are_batched_into_three_geometries() -> None:
    _, _, viewport = make_view_model()

    assert viewport.minorGridGeometry.vertex_count > viewport.majorGridGeometry.vertex_count > 0
    assert viewport.auxiliaryGridGeometry.vertex_count > 0


def test_orbit_updates_camera_without_rebuilding_the_grid() -> None:
    document, _, viewport = make_view_model()
    camera_changes = record(viewport.cameraChanged)
    grid_changes = record(viewport.gridChanged)
    camera_2d = document.workspace_state_2d

    viewport.orbitBy(40.0, -20.0)

    assert document.workspace_state_3d.azimuth == pytest.approx(-72.0)
    assert document.workspace_state_3d.elevation == pytest.approx(19.0)
    assert document.workspace_state_2d is camera_2d
    assert camera_changes and not grid_changes


def test_zooming_far_rebuilds_the_grid_with_a_coarser_step() -> None:
    _, _, viewport = make_view_model()
    grid_changes = record(viewport.gridChanged)
    extent = viewport.gridHalfExtent

    viewport.zoomBy(-120.0 * 12)

    assert grid_changes
    assert viewport.gridHalfExtent > extent


def test_camera_properties_follow_the_document() -> None:
    document, _, viewport = make_view_model()
    viewport.panBy(30.0, 10.0)

    view = viewport.viewport()
    position = viewport.cameraPosition
    assert (position.x(), position.y(), position.z()) == pytest.approx(view.scene_position, abs=1e-3)
    assert document.workspace_state_3d.target_x != 0.0


def test_projection_toggle_and_presets() -> None:
    document, _, viewport = make_view_model()

    viewport.toggleProjectionMode()
    assert viewport.projectionMode == "orthographic"
    viewport.applyPreset("top")
    assert document.workspace_state_3d.elevation == 89.0
    assert viewport.projectionMode == "orthographic"
    viewport.toggleProjectionMode()
    assert viewport.projectionMode == "perspective"


def test_unknown_preset_reports_an_error() -> None:
    document, view_model, viewport = make_view_model()

    viewport.applyPreset("isometric")

    assert "isometric" in view_model.errorMessage
    assert document.workspace_state_3d == CameraState3D()


def test_reset_restores_the_default_camera() -> None:
    document, _, viewport = make_view_model()
    viewport.orbitBy(100.0, 50.0)
    viewport.zoomBy(360.0)

    viewport.resetView()

    assert document.workspace_state_3d == CameraState3D()


def test_picking_at_the_centre_hits_the_target() -> None:
    _, _, viewport = make_view_model()

    hit = viewport.pickActivePlane(450.0, 300.0)
    viewport.setCursor(450.0, 300.0)

    assert hit["hit"] is True
    assert (hit["x"], hit["y"]) == pytest.approx((0.0, 0.0), abs=1e-9)
    assert viewport.cursorText == "XY plane: x = 0.00, y = 0.00"


def test_cursor_is_empty_when_the_ray_misses_the_plane() -> None:
    _, _, viewport = make_view_model()
    viewport.applyPreset("front")

    viewport.setCursor(450.0, 5.0)

    assert viewport.cursorText == ""
    assert viewport.pickActivePlane(450.0, 5.0)["hit"] is False


def test_labels_name_all_axes_and_keep_ticks_apart() -> None:
    _, _, viewport = make_view_model()
    labels = viewport.labels

    assert {label["text"] for label in labels if label["kind"] == "axis"} == {"x", "y", "z"}
    ticks = [label for label in labels if label["kind"] == "tick"]
    assert ticks
    for label in labels:
        assert 0.0 <= label["x"] <= 900.0 and 0.0 <= label["y"] <= 600.0


def test_tick_labels_near_the_horizon_are_decluttered() -> None:
    _, _, viewport = make_view_model()
    viewport.applyPreset("front")
    viewport.orbitBy(0.0, -20.0)

    ticks = [label for label in viewport.labels if label["kind"] == "tick"]
    assert ticks
    for axis in ("x", "y"):
        on_axis = [label for label in ticks if label["axis"] == axis]
        for index, first in enumerate(on_axis):
            for second in on_axis[index + 1:]:
                distance = math.hypot(first["x"] - second["x"], first["y"] - second["y"])
                assert distance >= MIN_TICK_LABEL_SPACING_PX


def test_auxiliary_planes_toggle() -> None:
    _, _, viewport = make_view_model()
    changes = record(viewport.auxiliaryPlanesVisibleChanged)

    viewport.toggleAuxiliaryPlanes()

    assert viewport.auxiliaryPlanesVisible is False
    assert len(changes) == 1


def test_3d_camera_survives_2d_work_and_workspace_switches() -> None:
    document, view_model, viewport = make_view_model()
    viewport.orbitBy(25.0, 5.0)
    viewport.panBy(-40.0, 12.0)
    camera = document.workspace_state_3d

    view_model.workspace.setWorkspaceMode("2d")
    view_model.viewport2D.setViewportSize(800.0, 600.0)
    view_model.viewport2D.panBy(10.0, 10.0)
    view_model.workspace.setWorkspaceMode("3d")

    assert document.workspace_state_3d == camera
    assert document.workspace_state_2d != CameraState2D()


def test_invalid_input_is_ignored() -> None:
    document, _, viewport = make_view_model()

    viewport.orbitBy(math.nan, 0.0)
    viewport.panBy(0.0, math.inf)
    viewport.zoomBy(math.nan)

    assert document.workspace_state_3d == CameraState3D()
