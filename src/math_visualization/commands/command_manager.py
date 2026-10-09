"""Executes commands and keeps the undo and redo history."""

from __future__ import annotations

from collections.abc import Callable

from math_visualization.commands.command import Command
from math_visualization.scene.scene_document import SceneDocument


class CommandManager:
    """The single entry point for edits of one document.

    Listeners are called with the command after every execute, undo and
    redo, so observers (view models) refresh from one place.
    """

    def __init__(
        self,
        document: SceneDocument,
        on_change: Callable[[Command], None] | None = None,
    ):
        self._document = document
        self._listeners: list[Callable[[Command], None]] = [on_change] if on_change else []
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    def execute(self, command: Command) -> None:
        """Apply ``command``; it raises before changing anything if the edit is invalid."""
        command.execute(self._document)
        if not (self._undo_stack and self._undo_stack[-1].merge(command)):
            self._undo_stack.append(command)
        self._redo_stack.clear()
        self._notify(command)

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        command.undo(self._document)
        self._redo_stack.append(command)
        self._notify(command)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        command.execute(self._document)
        self._undo_stack.append(command)
        self._notify(command)
        return True

    def add_listener(self, listener: Callable[[Command], None]) -> None:
        self._listeners.append(listener)

    def _notify(self, command: Command) -> None:
        for listener in self._listeners:
            listener(command)
