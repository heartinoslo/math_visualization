"""Transformation view model: the matrix, its presets and the current A(t)."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.commands import MATRIX_COMMANDS, Command, CommandManager, UpdateMatrixCommand
from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.math_core.transformations import (
    MATRIX_PRESETS,
    PRESETS_BY_KEY,
    ease,
    interpolate_from_identity,
)
from math_visualization.scene.matrix_object import MatrixObject
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.visual_state import VISUAL_FLAGS
from math_visualization.viewmodels.animation_viewmodel import AnimationViewModel
from math_visualization.viewmodels.formatting import format_number, parse_number
from math_visualization.viewmodels.scene_objects_viewmodel import SceneObjectsViewModel


ENTRY_NAMES = ("a", "b", "c", "d")


def format_matrix(matrix: Matrix2, decimals: int = 2) -> str:
    rows = (
        f"{format_number(first, decimals)}  {format_number(second, decimals)}"
        for first, second in matrix.rows
    )
    return "[ " + " ; ".join(rows) + " ]"


class TransformationViewModel(QObject):
    """Edits the document matrix through commands and publishes ``A(t)``.

    ``currentMatrixChanged`` fires whenever the matrix or the animation
    parameter changes; renderers read :meth:`current_matrix` then.
    """

    matrixChanged = Signal()
    currentMatrixChanged = Signal()
    visualStateChanged = Signal()
    expressionChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        commands: CommandManager,
        animation: AnimationViewModel,
        scene: SceneObjectsViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._commands = commands
        self._animation = animation
        self._current = self._compute_current()
        commands.add_listener(self._on_command)
        animation.progressChanged.connect(self._refresh_current)
        scene.vectorsChanged.connect(self.expressionChanged)
        scene.selectionChanged.connect(self.expressionChanged)

    # Python API used by the viewports -----------------------------------------------

    def current_matrix(self) -> Matrix2:
        return self._current

    @property
    def parameter(self) -> float:
        """The eased transformation parameter ``t``."""
        state = self._document.animation_state
        return ease(state.progress, state.rate_function)

    @property
    def is_identity_now(self) -> bool:
        return self._current == Matrix2.identity()

    def _compute_current(self) -> Matrix2:
        return interpolate_from_identity(self._document.matrix, self.parameter)

    def _refresh_current(self) -> None:
        current = self._compute_current()
        if current != self._current:
            self._current = current
            self.currentMatrixChanged.emit()
        self.expressionChanged.emit()

    def reload(self) -> None:
        """The document was replaced (a project was opened): publish its matrix and options."""
        self._current = self._compute_current()
        self.matrixChanged.emit()
        self.currentMatrixChanged.emit()
        self.visualStateChanged.emit()
        self.expressionChanged.emit()

    def _on_command(self, command: Command) -> None:
        if isinstance(command, MATRIX_COMMANDS):
            self.active_matrix_changed()

    def active_matrix_changed(self) -> None:
        """The active matrix, or its value, changed: republish it and A(t)."""
        self.matrixChanged.emit()
        self._refresh_current()

    # Matrix editing ------------------------------------------------------------------

    @Property(bool, notify=matrixChanged)
    def hasMatrix(self) -> bool:
        return self._document.active_matrix is not None

    @Property(str, notify=matrixChanged)
    def matrixName(self) -> str:
        """Name of the active matrix ("A" when there is none, for the formulas)."""
        active = self._document.active_matrix
        return active.name if active is not None else "A"

    @Property("QStringList", notify=matrixChanged)
    def entryTexts(self) -> list[str]:
        return [format_number(value) for value in self._document.matrix.entries]

    @Slot(int, str, result=bool)
    def setEntryText(self, index: int, text: str) -> bool:
        if not 0 <= index < 4:
            return False
        try:
            value = parse_number(text)
        except ValueError as error:
            self.errorOccurred.emit(f"Matrix entry {ENTRY_NAMES[index]}: {error}")
            return False
        entries = list(self._document.matrix.entries)
        entries[index] = value
        return self.set_matrix(Matrix2(*entries))

    @Property("QVariantList", constant=True)
    def presets(self) -> list[dict]:
        return [{"key": preset.key, "label": preset.label} for preset in MATRIX_PRESETS]

    @Slot(str, result=bool)
    def applyPreset(self, key: str) -> bool:
        preset = PRESETS_BY_KEY.get(key)
        if preset is None:
            self.errorOccurred.emit(f"Unknown matrix preset: {key!r}")
            return False
        return self.set_matrix(preset.matrix)

    def set_matrix(self, matrix: Matrix2) -> bool:
        """Replace the active matrix's entries through an undoable command."""
        active = self._document.active_matrix
        if active is None:
            self.errorOccurred.emit("There is no matrix to edit; add one first")
            return False
        if matrix != active.matrix:
            self._commands.execute(UpdateMatrixCommand(active, MatrixObject(active.object_id, active.name, matrix)))
        return True

    # Visibility of the transformation layers ---------------------------------------------

    @Property("QVariantMap", notify=visualStateChanged)
    def visualState(self) -> dict:
        state = self._document.visual_state
        return {name: getattr(state, name) for name in VISUAL_FLAGS}

    @Slot(str, bool)
    def setVisualFlag(self, name: str, value: bool) -> None:
        if name not in VISUAL_FLAGS:
            self.errorOccurred.emit(f"Unknown display option: {name!r}")
            return
        state = replace(self._document.visual_state, **{name: value})
        if state != self._document.visual_state:
            self._document.visual_state = state
            self.visualStateChanged.emit()

    # Expression panel -------------------------------------------------------------------

    @Property(str, notify=matrixChanged)
    def targetText(self) -> str:
        return f"{self.matrixName} = " + format_matrix(self._document.matrix)

    @Property(str, notify=expressionChanged)
    def parameterText(self) -> str:
        state = self._document.animation_state
        return f"t = {state.rate_function}(τ) = {self.parameter:.3f}   (τ = {state.progress:.3f})"

    @Property(str, notify=expressionChanged)
    def currentText(self) -> str:
        name = self.matrixName
        return f"{name}(t) = (1 − t)·I + t·{name} = " + format_matrix(self._current)

    @Property(str, notify=expressionChanged)
    def selectedMappingText(self) -> str:
        selected = self._document.find_vector(self._document.selected_object_id)
        if selected is None:
            return ""
        image = self._current @ selected.vector
        name = self.matrixName
        return (
            f"{name}(t)·{selected.name} = {name}(t)·({format_number(selected.vector.x, 2)}, "
            f"{format_number(selected.vector.y, 2)}) = ({format_number(image.x, 2)}, "
            f"{format_number(image.y, 2)})"
        )
