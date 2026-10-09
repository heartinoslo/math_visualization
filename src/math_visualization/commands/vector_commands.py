"""Commands that add, remove and update vectors."""

from __future__ import annotations

from math_visualization.commands.command import Command
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import VectorObject


class AddVectorCommand(Command):
    """Insert a vector (at the end by default) and select it."""

    def __init__(self, vector: VectorObject, index: int | None = None):
        self.vector = vector
        self._index = index
        self._previous_selection: str | None = None

    @property
    def label(self) -> str:
        return f"Add {self.vector.name}"

    def execute(self, document: SceneDocument) -> None:
        if document.find_vector(self.vector.object_id) is not None:
            raise ValueError(f"A vector with id {self.vector.object_id!r} already exists")
        index = len(document.vectors) if self._index is None else self._index
        self._previous_selection = document.selected_object_id
        document.vectors.insert(index, self.vector)
        document.selected_object_id = self.vector.object_id

    def undo(self, document: SceneDocument) -> None:
        del document.vectors[document.vector_index(self.vector.object_id)]
        document.selected_object_id = self._previous_selection


class RemoveVectorCommand(Command):
    """Delete a vector; undo restores it at its original position."""

    def __init__(self, object_id: str):
        self.object_id = object_id
        self._removed: VectorObject | None = None
        self._index = 0
        self._previous_selection: str | None = None

    @property
    def label(self) -> str:
        return f"Delete {self._removed.name}" if self._removed is not None else "Delete vector"

    def execute(self, document: SceneDocument) -> None:
        self._index = document.vector_index(self.object_id)
        self._removed = document.vectors.pop(self._index)
        self._previous_selection = document.selected_object_id
        if document.selected_object_id == self.object_id:
            document.selected_object_id = None

    def undo(self, document: SceneDocument) -> None:
        document.vectors.insert(self._index, self._removed)
        document.selected_object_id = self._previous_selection


class UpdateVectorCommand(Command):
    """Replace a vector's value, name or colour.

    Updates sharing a non-empty ``merge_key`` (one pointer drag) merge into a
    single undo step that spans from the first ``before`` to the last ``after``.
    """

    def __init__(self, before: VectorObject, after: VectorObject, merge_key: str | None = None):
        if before.object_id != after.object_id:
            raise ValueError("before and after must describe the same vector")
        self.before = before
        self.after = after
        self.merge_key = merge_key

    @property
    def object_id(self) -> str:
        return self.after.object_id

    @property
    def label(self) -> str:
        if self.before.name != self.after.name:
            return f"Rename {self.before.name}"
        if self.before.color != self.after.color:
            return f"Recolor {self.after.name}"
        return f"Move {self.after.name}"

    def execute(self, document: SceneDocument) -> None:
        document.vectors[document.vector_index(self.object_id)] = self.after

    def undo(self, document: SceneDocument) -> None:
        document.vectors[document.vector_index(self.object_id)] = self.before

    def merge(self, newer: Command) -> bool:
        if (
            isinstance(newer, UpdateVectorCommand)
            and self.merge_key is not None
            and newer.merge_key == self.merge_key
            and newer.object_id == self.object_id
        ):
            self.after = newer.after
            return True
        return False
