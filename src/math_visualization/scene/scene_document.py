"""Domain model for one mathematical visualization document."""

from dataclasses import dataclass, field
from uuid import uuid4

from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.vector_object import VectorObject
from math_visualization.scene.visual_state import VisualState
from math_visualization.scene.workspace_state import (
    CameraState2D,
    CameraState3D,
    WorkspaceMode,
)


@dataclass
class SceneDocument:
    """Renderer-independent document state shared by every workspace.

    ``vectors`` keeps creation order, which is also the drawing order; they are
    the inputs of the transformation by ``matrix``. Mutate vectors and the
    matrix through :mod:`math_visualization.commands` so every change can be
    undone.
    """

    title: str = "Untitled"
    schema_version: int = 1
    document_id: str = field(default_factory=lambda: uuid4().hex)
    workspace_mode: WorkspaceMode = WorkspaceMode.TWO_D
    workspace_state_2d: CameraState2D = field(default_factory=CameraState2D)
    workspace_state_3d: CameraState3D = field(default_factory=CameraState3D)
    animation_state: AnimationState = field(default_factory=AnimationState)
    vectors: list[VectorObject] = field(default_factory=list)
    selected_object_id: str | None = None
    matrix: Matrix2 = field(default_factory=Matrix2.identity)
    visual_state: VisualState = field(default_factory=VisualState)

    def vector_index(self, object_id: str) -> int:
        """Return the position of ``object_id`` in ``vectors`` or raise ``KeyError``."""
        for index, vector in enumerate(self.vectors):
            if vector.object_id == object_id:
                return index
        raise KeyError(object_id)

    def find_vector(self, object_id: str | None) -> VectorObject | None:
        if object_id is None:
            return None
        try:
            return self.vectors[self.vector_index(object_id)]
        except KeyError:
            return None
