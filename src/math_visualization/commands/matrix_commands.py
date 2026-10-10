"""Commands that add, remove and edit named matrices.

Each command makes the matrix it touches the active one, on execute and on
undo, so the user always sees the edit being applied or reverted; the views
then show that matrix rather than a computed operation.
"""

from __future__ import annotations

from math_visualization.commands.command import Command
from math_visualization.scene.matrix_object import MatrixObject
from math_visualization.scene.scene_document import SceneDocument


class AddMatrixCommand(Command):
    """Insert a matrix (at the end by default) and make it active."""

    def __init__(self, matrix: MatrixObject, index: int | None = None):
        self.matrix = matrix
        self._index = index
        self._previous_active: str | None = None
        self._previous_operation: str | None = None

    @property
    def label(self) -> str:
        return f"Add {self.matrix.name}"

    def execute(self, document: SceneDocument) -> None:
        if document.find_matrix(self.matrix.object_id) is not None:
            raise ValueError(f"A matrix with id {self.matrix.object_id!r} already exists")
        index = len(document.matrices) if self._index is None else self._index
        self._previous_active = document.active_matrix_id
        self._previous_operation = document.active_operation_id
        document.matrices.insert(index, self.matrix)
        document.active_matrix_id = self.matrix.object_id
        document.active_operation_id = None

    def undo(self, document: SceneDocument) -> None:
        del document.matrices[document.matrix_index(self.matrix.object_id)]
        document.active_matrix_id = self._previous_active
        document.active_operation_id = self._previous_operation


class RemoveMatrixCommand(Command):
    """Delete a matrix; if it was active, its neighbour becomes active. Undo restores both."""

    def __init__(self, object_id: str):
        self.object_id = object_id
        self._removed: MatrixObject | None = None
        self._index = 0
        self._previous_active: str | None = None

    @property
    def label(self) -> str:
        return f"Delete {self._removed.name}" if self._removed is not None else "Delete matrix"

    def execute(self, document: SceneDocument) -> None:
        self._index = document.matrix_index(self.object_id)
        self._previous_active = document.active_matrix_id
        self._removed = document.matrices.pop(self._index)
        if document.active_matrix_id == self.object_id:
            remaining = document.matrices
            document.active_matrix_id = (
                remaining[min(self._index, len(remaining) - 1)].object_id if remaining else None
            )

    def undo(self, document: SceneDocument) -> None:
        document.matrices.insert(self._index, self._removed)
        document.active_matrix_id = self._previous_active


class UpdateMatrixCommand(Command):
    """Replace a matrix's entries or name, and make it active."""

    def __init__(self, before: MatrixObject, after: MatrixObject):
        if before.object_id != after.object_id:
            raise ValueError("before and after must describe the same matrix")
        self.before = before
        self.after = after

    @property
    def object_id(self) -> str:
        return self.after.object_id

    @property
    def label(self) -> str:
        if self.before.name != self.after.name:
            return f"Rename {self.before.name}"
        return f"Edit {self.after.name}"

    def execute(self, document: SceneDocument) -> None:
        document.matrices[document.matrix_index(self.object_id)] = self.after
        document.active_matrix_id = self.object_id
        document.active_operation_id = None

    def undo(self, document: SceneDocument) -> None:
        document.matrices[document.matrix_index(self.object_id)] = self.before
        document.active_matrix_id = self.object_id
        document.active_operation_id = None


MATRIX_COMMANDS = (AddMatrixCommand, RemoveMatrixCommand, UpdateMatrixCommand)
