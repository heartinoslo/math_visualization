"""Commands that record and delete matrix operations."""

from __future__ import annotations

from math_visualization.commands.command import Command
from math_visualization.scene.matrix_object import MatrixObject
from math_visualization.scene.operation_record import OperationRecord
from math_visualization.scene.scene_document import SceneDocument


class AddOperationCommand(Command):
    """Record an operation and add its result matrix (if any) in one undoable step.

    The operation becomes the focus and its result the active matrix.
    """

    def __init__(self, operation: OperationRecord, result: MatrixObject | None = None):
        self.operation = operation
        self.result = result
        self._previous_matrix: str | None = None
        self._previous_operation: str | None = None

    @property
    def label(self) -> str:
        return f"Compute {self.operation.title}"

    def execute(self, document: SceneDocument) -> None:
        self._previous_matrix = document.active_matrix_id
        self._previous_operation = document.active_operation_id
        document.operations.append(self.operation)
        if self.result is not None:
            document.matrices.append(self.result)
            document.active_matrix_id = self.result.object_id
        document.active_operation_id = self.operation.object_id

    def undo(self, document: SceneDocument) -> None:
        del document.operations[document.operation_index(self.operation.object_id)]
        if self.result is not None:
            del document.matrices[document.matrix_index(self.result.object_id)]
        document.active_matrix_id = self._previous_matrix
        document.active_operation_id = self._previous_operation


class RemoveOperationCommand(Command):
    """Delete an operation record (its result matrix stays)."""

    def __init__(self, object_id: str):
        self.object_id = object_id
        self._removed: OperationRecord | None = None
        self._index = 0
        self._previous_operation: str | None = None

    @property
    def label(self) -> str:
        return f"Delete {self._removed.title}" if self._removed is not None else "Delete operation"

    def execute(self, document: SceneDocument) -> None:
        self._index = document.operation_index(self.object_id)
        self._previous_operation = document.active_operation_id
        self._removed = document.operations.pop(self._index)
        if document.active_operation_id == self.object_id:
            document.active_operation_id = None

    def undo(self, document: SceneDocument) -> None:
        document.operations.insert(self._index, self._removed)
        document.active_operation_id = self._previous_operation


OPERATION_COMMANDS = (AddOperationCommand, RemoveOperationCommand)
