"""Tests for the 2D viewport view model."""

import math

from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import CameraState2D, WorkspaceMode
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def make_view_model():
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    viewport = view_model.viewport2D
    viewport.setViewportSize(800.0, 600.0)
    return document, view_model, viewport


def test_viewport_size_publishes_grid() -> None:
    _, _, viewport = make_view_model()

    assert (viewport.originX, viewport.originY) == (400.0, 300.0)
    assert viewport.majorX and viewport.minorY
    assert {"position": 480.0, "text": "1"} in viewport.xLabels


def test_pan_changes_only_the_2d_camera() -> None:
    document, _, viewport = make_view_model()
    camera_3d = document.workspace_state_3d
    animation = document.animation_state
    changes: list = []
    viewport.gridChanged.connect(lambda: changes.append(True))

    viewport.panBy(80.0, 40.0)

    assert document.workspace_state_2d == CameraState2D(-1.0, 0.5, 1.0)
    assert document.workspace_state_3d is camera_3d
    assert document.animation_state is animation
    assert document.workspace_mode is WorkspaceMode.TWO_D
    assert (viewport.originX, viewport.originY) == (480.0, 340.0)
    assert changes


def test_wheel_zoom_keeps_cursor_point_fixed() -> None:
    document, _, viewport = make_view_model()
    viewport.setCursor(600.0, 100.0)
    before = viewport.cursorText

    viewport.zoomAt(600.0, 100.0, 240.0)

    assert math.isclose(document.workspace_state_2d.zoom, 1.15**2)
    assert viewport.cursorText == before


def test_reset_view_restores_default_camera() -> None:
    document, _, viewport = make_view_model()
    viewport.panBy(10.0, 10.0)
    viewport.zoomAt(0.0, 0.0, 120.0)

    viewport.resetView()

    assert document.workspace_state_2d == CameraState2D()


def test_cursor_text_reports_mathematical_coordinates() -> None:
    _, _, viewport = make_view_model()

    viewport.setCursor(480.0, 220.0)
    assert viewport.cursorText == "x = 1.00, y = 1.00"

    viewport.clearCursor()
    assert viewport.cursorText == ""


def test_camera_summary_and_grid_follow_external_camera_changes() -> None:
    _, view_model, viewport = make_view_model()

    view_model.workspace.setCamera2D(1.0, -2.0, 1.5)

    assert viewport.cameraSummary == "Center (1.00, -2.00) · Zoom 1.50×"
    assert viewport.originX == 400.0 - 1.0 * 80.0 * 1.5


def test_invalid_input_is_ignored() -> None:
    document, _, viewport = make_view_model()

    viewport.panBy(math.nan, 0.0)
    viewport.zoomAt(0.0, 0.0, math.inf)
    viewport.setViewportSize(math.nan, 10.0)

    assert document.workspace_state_2d == CameraState2D()
    assert viewport.viewportWidth == 800.0
