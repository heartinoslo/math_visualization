"""Command that changes the transformation matrix."""

from __future__ import annotations

from math_visualization.commands.command import Command
from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.scene.scene_document import SceneDocument


class SetMatrixCommand(Command):
    label = "Edit matrix"

    def __init__(self, before: Matrix2, after: Matrix2):
        self.before = before
        self.after = after

    def execute(self, document: SceneDocument) -> None:
        document.matrix = self.after

    def undo(self, document: SceneDocument) -> None:
        document.matrix = self.before
