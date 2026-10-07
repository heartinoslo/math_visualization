"""Base class for undoable edits of a scene document."""

from __future__ import annotations

from abc import ABC, abstractmethod

from math_visualization.scene.scene_document import SceneDocument


class Command(ABC):
    """An edit that knows how to apply itself and how to revert itself.

    ``execute`` and ``undo`` must be exact inverses, and ``execute`` must be
    safe to call again after ``undo`` (that is what redo does).
    """

    label: str = "Edit"

    @abstractmethod
    def execute(self, document: SceneDocument) -> None:
        """Apply the edit."""

    @abstractmethod
    def undo(self, document: SceneDocument) -> None:
        """Revert the edit."""

    def merge(self, newer: Command) -> bool:
        """Absorb ``newer`` (already executed) into this command if they are one edit.

        Returning ``True`` keeps a single undo step, as for the many small
        updates a pointer drag produces.
        """
        return False
