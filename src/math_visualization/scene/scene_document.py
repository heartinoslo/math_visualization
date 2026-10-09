"""Domain model for one mathematical visualization document."""

from dataclasses import dataclass, field, fields
from uuid import uuid4

from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.matrix_object import MatrixObject, new_object_id
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
    the inputs of the transformation. ``matrices`` are the named matrices; the
    active one is edited and played (``active_matrix_id`` is ``None`` only
    when there are none). Mutate vectors and matrices through
    :mod:`math_visualization.commands` so every change can be undone.
    """

    title: str = "Untitled"
    schema_version: int = 2
    document_id: str = field(default_factory=lambda: uuid4().hex)
    workspace_mode: WorkspaceMode = WorkspaceMode.TWO_D
    workspace_state_2d: CameraState2D = field(default_factory=CameraState2D)
    workspace_state_3d: CameraState3D = field(default_factory=CameraState3D)
    animation_state: AnimationState = field(default_factory=AnimationState)
    vectors: list[VectorObject] = field(default_factory=list)
    selected_object_id: str | None = None
    matrices: list[MatrixObject] = field(
        default_factory=lambda: [MatrixObject(new_object_id(), "A", Matrix2.identity())]
    )
    active_matrix_id: str | None = None
    visual_state: VisualState = field(default_factory=VisualState)

    def __post_init__(self) -> None:
        if self.active_matrix_id is None and self.matrices:
            self.active_matrix_id = self.matrices[0].object_id

    # Matrices -------------------------------------------------------------------

    def matrix_index(self, object_id: str) -> int:
        """Return the position of ``object_id`` in ``matrices`` or raise ``KeyError``."""
        for index, matrix in enumerate(self.matrices):
            if matrix.object_id == object_id:
                return index
        raise KeyError(object_id)

    def find_matrix(self, object_id: str | None) -> MatrixObject | None:
        if object_id is None:
            return None
        try:
            return self.matrices[self.matrix_index(object_id)]
        except KeyError:
            return None

    @property
    def active_matrix(self) -> MatrixObject | None:
        return self.find_matrix(self.active_matrix_id)

    @property
    def matrix(self) -> Matrix2:
        """The transformation being shown: the active matrix, or I when there is none."""
        active = self.active_matrix
        return active.matrix if active is not None else Matrix2.identity()

    @matrix.setter
    def matrix(self, value: Matrix2) -> None:
        """Set the active matrix's value directly (tests and scripts; the UI uses commands)."""
        active = self.active_matrix
        if active is None:
            active = MatrixObject(new_object_id(), "A", value)
            self.matrices.append(active)
            self.active_matrix_id = active.object_id
        else:
            self.matrices[self.matrix_index(active.object_id)] = MatrixObject(active.object_id, active.name, value)

    # Vectors --------------------------------------------------------------------

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

    def replace_contents(self, other: "SceneDocument") -> None:
        """Become ``other`` in place, so every view model keeps its reference."""
        for item in fields(self):
            setattr(self, item.name, getattr(other, item.name))
