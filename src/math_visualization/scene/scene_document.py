"""Domain model for one mathematical visualization document."""

from dataclasses import dataclass, field
from uuid import uuid4

from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.workspace_state import (
    CameraState2D,
    CameraState3D,
    WorkspaceMode,
)


@dataclass
class SceneDocument:
    """Renderer-independent document state shared by every workspace."""

    title: str = "Untitled"
    schema_version: int = 1
    document_id: str = field(default_factory=lambda: uuid4().hex)
    workspace_mode: WorkspaceMode = WorkspaceMode.TWO_D
    workspace_state_2d: CameraState2D = field(default_factory=CameraState2D)
    workspace_state_3d: CameraState3D = field(default_factory=CameraState3D)
    animation_state: AnimationState = field(default_factory=AnimationState)
