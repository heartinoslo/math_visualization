"""Tests for renderer-independent workspace and animation state."""

import math

import pytest

from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import (
    CameraState2D,
    CameraState3D,
    ProjectionMode,
    WorkspaceMode,
)


def test_document_defaults_to_2d_with_default_cameras_and_progress() -> None:
    document = SceneDocument()

    assert document.workspace_mode is WorkspaceMode.TWO_D
    assert document.workspace_state_2d == CameraState2D()
    assert document.workspace_state_3d == CameraState3D()
    assert document.animation_state == AnimationState()


def test_documents_do_not_share_mutable_defaults() -> None:
    first = SceneDocument()
    second = SceneDocument()
    first.workspace_mode = WorkspaceMode.THREE_D

    assert second.workspace_mode is WorkspaceMode.TWO_D


def test_workspace_mode_parses_serialized_values() -> None:
    assert WorkspaceMode("3d") is WorkspaceMode.THREE_D
    with pytest.raises(ValueError):
        WorkspaceMode("4d")


@pytest.mark.parametrize(
    "arguments",
    [
        {"zoom": 0.0},
        {"zoom": -1.0},
        {"center_x": math.nan},
        {"center_y": math.inf},
    ],
)
def test_camera_2d_rejects_invalid_values(arguments) -> None:
    with pytest.raises(ValueError):
        CameraState2D(**arguments)


@pytest.mark.parametrize(
    "arguments",
    [
        {"distance": 0.0},
        {"elevation": 91.0},
        {"azimuth": math.nan},
        {"target_z": math.inf},
        {"projection_mode": "fisheye"},
    ],
)
def test_camera_3d_rejects_invalid_values(arguments) -> None:
    with pytest.raises(ValueError):
        CameraState3D(**arguments)


def test_camera_3d_normalizes_projection_mode() -> None:
    camera = CameraState3D(projection_mode="orthographic")

    assert camera.projection_mode is ProjectionMode.ORTHOGRAPHIC


@pytest.mark.parametrize(
    "arguments",
    [{"progress": -0.1}, {"progress": 1.1}, {"progress": math.nan}, {"duration": 0.0}],
)
def test_animation_state_rejects_invalid_values(arguments) -> None:
    with pytest.raises(ValueError):
        AnimationState(**arguments)
