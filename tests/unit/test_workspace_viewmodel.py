"""Tests for Python-managed workspace, animation, theme and error state."""

from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import CameraState2D, CameraState3D, WorkspaceMode
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def record(signal) -> list:
    emissions: list = []
    signal.connect(lambda *arguments: emissions.append(arguments))
    return emissions


def test_switching_workspace_updates_mode_without_replacing_document() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    workspace = view_model.workspace
    changes = record(workspace.workspaceModeChanged)

    workspace.setWorkspaceMode("3d")

    assert workspace.workspaceMode == "3d"
    assert view_model.document is document
    assert document.workspace_mode is WorkspaceMode.THREE_D
    assert len(changes) == 1


def test_selecting_current_workspace_does_not_notify() -> None:
    view_model = ApplicationViewModel(SceneDocument())
    workspace = view_model.workspace
    changes = record(workspace.workspaceModeChanged)

    workspace.setWorkspaceMode("2d")

    assert changes == []


def test_each_workspace_keeps_its_own_camera_across_switches() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    workspace = view_model.workspace

    workspace.setCamera2D(1.5, -2.0, 3.0)
    workspace.setWorkspaceMode("3d")
    workspace.setCamera3D(0.0, 1.0, 0.0, 120.0, 15.0, 8.0)
    workspace.setProjectionMode3D("orthographic")
    workspace.setWorkspaceMode("2d")
    workspace.setWorkspaceMode("3d")

    assert workspace.camera2D == {"centerX": 1.5, "centerY": -2.0, "zoom": 3.0}
    assert workspace.camera3D == {
        "targetX": 0.0,
        "targetY": 1.0,
        "targetZ": 0.0,
        "azimuth": 120.0,
        "elevation": 15.0,
        "distance": 8.0,
        "projectionMode": "orthographic",
    }


def test_camera_changes_notify_only_their_own_workspace() -> None:
    view_model = ApplicationViewModel(SceneDocument())
    workspace = view_model.workspace
    changes_2d = record(workspace.camera2DChanged)
    changes_3d = record(workspace.camera3DChanged)

    workspace.setCamera2D(1.0, 0.0, 1.0)

    assert len(changes_2d) == 1
    assert changes_3d == []


def test_camera_resets_restore_defaults() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    workspace = view_model.workspace
    workspace.setCamera2D(4.0, 4.0, 2.0)
    workspace.setCamera3D(1.0, 1.0, 1.0, 10.0, 10.0, 3.0)

    workspace.resetCamera2D()
    workspace.resetCamera3D()

    assert document.workspace_state_2d == CameraState2D()
    assert document.workspace_state_3d == CameraState3D()


def test_invalid_requests_report_errors_and_keep_state() -> None:
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    workspace = view_model.workspace

    workspace.setWorkspaceMode("4d")
    assert "4d" in view_model.errorMessage
    workspace.setCamera2D(0.0, 0.0, 0.0)
    assert "zoom" in view_model.errorMessage
    workspace.setProjectionMode3D("fisheye")
    assert "3D camera" in view_model.errorMessage
    view_model.animation.setProgress(2.0)
    assert "progress" in view_model.errorMessage

    assert document.workspace_mode is WorkspaceMode.TWO_D
    assert document.workspace_state_2d == CameraState2D()
    assert document.workspace_state_3d == CameraState3D()
    assert document.animation_state.progress == 0.0


def test_clear_error_resets_message_once() -> None:
    view_model = ApplicationViewModel(SceneDocument())
    changes = record(view_model.errorMessageChanged)

    view_model.reportError("Something failed")
    view_model.clearError()
    view_model.clearError()

    assert view_model.errorMessage == ""
    assert len(changes) == 2


def test_animation_progress_survives_workspace_switches() -> None:
    view_model = ApplicationViewModel(SceneDocument())
    changes = record(view_model.animation.progressChanged)

    view_model.animation.setProgress(0.4)
    view_model.workspace.setWorkspaceMode("3d")
    view_model.workspace.setWorkspaceMode("2d")

    assert view_model.animation.progress == 0.4
    assert len(changes) == 1


def test_theme_mode_toggles_and_rejects_unknown_values() -> None:
    view_model = ApplicationViewModel(SceneDocument())
    changes = record(view_model.themeModeChanged)

    assert view_model.themeMode == "dark"
    view_model.toggleThemeMode()
    assert view_model.themeMode == "light"
    view_model.setThemeMode("sepia")

    assert view_model.themeMode == "light"
    assert "sepia" in view_model.errorMessage
    assert len(changes) == 1
