"""Executes commands and keeps the undo and redo history."""

from __future__ import annotations

from collections.abc import Callable

from math_visualization.commands.command import Command
from math_visualization.scene.scene_document import SceneDocument


class CommandManager:
    """The single entry point for edits of one document.

    Listeners are called with the command after every execute, undo and
    redo, so observers (view models) refresh from one place.

    It also remembers which history position was last saved: the document is
    clean while the top of the undo stack is the command that was on top at
    :meth:`mark_clean`. Undoing and redoing back to that point makes it clean
    again; once that point is unreachable (it was merged into, or discarded
    from the redo stack) the document stays dirty until the next save.
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
        self._clean_top: Command | None = None
        self._clean_reachable = True

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def undo_label(self) -> str:
        """Label of the edit :meth:`undo` would revert, or ``""``."""
        return self._undo_stack[-1].label if self._undo_stack else ""

    @property
    def redo_label(self) -> str:
        return self._redo_stack[-1].label if self._redo_stack else ""

    @property
    def is_clean(self) -> bool:
        """Whether the document matches the last :meth:`mark_clean` (the last save)."""
        return self._clean_reachable and self._top is self._clean_top

    @property
    def _top(self) -> Command | None:
        return self._undo_stack[-1] if self._undo_stack else None

    def mark_clean(self) -> None:
        self._clean_top = self._top
        self._clean_reachable = True

    def clear(self) -> None:
        """Forget the whole history (a document was opened or created); it is clean."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.mark_clean()

    def execute(self, command: Command) -> None:
        """Apply ``command``; it raises before changing anything if the edit is invalid."""
        command.execute(self._document)
        top = self._top
        if top is not None and top.merge(command):
            if top is self._clean_top:
                # The saved state was inside this merged edit; it no longer exists.
                self._clean_reachable = False
        else:
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
