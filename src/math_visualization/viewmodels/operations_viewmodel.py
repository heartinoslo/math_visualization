"""Operations view model: computing matrix operations and explaining them step by step."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Property, Qt, Signal, Slot

from math_visualization.commands import (
    MATRIX_COMMANDS,
    OPERATION_COMMANDS,
    AddOperationCommand,
    Command,
    CommandManager,
    RemoveOperationCommand,
)
from math_visualization.math_core.matrix_algebra import OPERATION_LABELS, OperationKind, check, compute
from math_visualization.math_core.transformations import ease
from math_visualization.scene.matrix_object import MatrixObject, new_object_id, next_matrix_name
from math_visualization.scene.operation_record import OperationRecord
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.algebra_view import matrix_view, operation_view, step_at
from math_visualization.viewmodels.animation_viewmodel import AnimationViewModel
from math_visualization.viewmodels.formatting import parse_number
from math_visualization.viewmodels.transformation_viewmodel import TransformationViewModel
from math_visualization.viewport.matrix_figures import FigureScene, matrix_scene, operation_scene


class OperationListModel(QAbstractListModel):
    ObjectIdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ActiveRole = Qt.UserRole + 3

    def __init__(self, document: SceneDocument, parent: QObject | None = None):
        super().__init__(parent)
        self._document = document

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._document.operations)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._document.operations):
            return None
        operation = self._document.operations[index.row()]
        if role in (Qt.DisplayRole, self.TitleRole):
            return operation.title
        if role == self.ObjectIdRole:
            return operation.object_id
        if role == self.ActiveRole:
            return operation.object_id == self._document.active_operation_id
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ObjectIdRole: QByteArray(b"objectId"),
            self.TitleRole: QByteArray(b"title"),
            self.ActiveRole: QByteArray(b"active"),
        }

    def reset(self) -> None:
        self.beginResetModel()
        self.endResetModel()


class OperationsViewModel(QObject):
    """Computes operations on the document's matrices and drives their explanation.

    The focused operation (if any) is what the Algebra view derives and what
    the 2D/3D views animate; playback runs one segment per derivation step.
    """

    operationsChanged = Signal()
    focusChanged = Signal()
    choicesChanged = Signal()
    viewChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        commands: CommandManager,
        transformation: TransformationViewModel,
        animation: AnimationViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._commands = commands
        self._transformation = transformation
        self._animation = animation
        self._model = OperationListModel(document, self)
        self._last_focus = document.active_operation_id
        commands.add_listener(self._on_command)
        transformation.matrixChanged.connect(self._sync_focus)
        animation.progressChanged.connect(self.viewChanged)
        self._update_segments()

    # Observation ------------------------------------------------------------------------

    def _on_command(self, command: Command) -> None:
        if isinstance(command, OPERATION_COMMANDS):
            self._model.reset()
            self.operationsChanged.emit()
        if isinstance(command, MATRIX_COMMANDS + OPERATION_COMMANDS):
            self.choicesChanged.emit()
        self._sync_focus()
        self.viewChanged.emit()

    def _sync_focus(self) -> None:
        if self._document.active_operation_id != self._last_focus:
            self._last_focus = self._document.active_operation_id
            self._model.reset()
            self._update_segments()
            self.focusChanged.emit()
        self.viewChanged.emit()

    def _update_segments(self) -> None:
        operation = self._document.active_operation
        self._animation.set_segments(len(operation.derivation.steps) if operation is not None else 1)

    def reload(self) -> None:
        self._model.reset()
        self._last_focus = self._document.active_operation_id
        self._update_segments()
        self.operationsChanged.emit()
        self.choicesChanged.emit()
        self.focusChanged.emit()
        self.viewChanged.emit()

    # Lists for QML ------------------------------------------------------------------------

    @Property(QObject, constant=True)
    def operationModel(self) -> OperationListModel:
        return self._model

    @Property(int, notify=operationsChanged)
    def operationCount(self) -> int:
        return len(self._document.operations)

    @Property(str, notify=focusChanged)
    def activeId(self) -> str:
        return self._document.active_operation_id or ""

    @Property(bool, notify=focusChanged)
    def hasFocus(self) -> bool:
        return self._document.active_operation_id is not None

    @Property("QVariantList", constant=True)
    def kinds(self) -> list[dict]:
        return [
            {"key": kind.value, "label": OPERATION_LABELS[kind], "operands": kind.operand_count, "needsScalar": kind.needs_scalar}
            for kind in OperationKind
        ]

    @Property("QVariantList", notify=choicesChanged)
    def operandChoices(self) -> list[dict]:
        return [
            {"id": matrix.object_id, "name": matrix.name, "size": matrix.size, "label": f"{matrix.name}  ({matrix.size}×{matrix.size})"}
            for matrix in self._document.matrices
        ]

    # Computing ------------------------------------------------------------------------------

    @Slot(str, str, str, str, result=bool)
    def compute(self, kind_key: str, left_id: str, right_id: str, scalar_text: str) -> bool:
        """Compute an operation from the form; the result becomes a new matrix and the focus."""
        try:
            kind = OperationKind(kind_key)
        except ValueError:
            self.errorOccurred.emit(f"Unknown operation: {kind_key!r}")
            return False
        ids = [left_id, right_id][: kind.operand_count]
        matrices = [self._document.find_matrix(identifier) for identifier in ids]
        if any(matrix is None for matrix in matrices):
            self.errorOccurred.emit(f"{OPERATION_LABELS[kind]} needs {kind.operand_count} existing matrices")
            return False
        scalar = None
        if kind.needs_scalar:
            try:
                scalar = parse_number(scalar_text)
            except ValueError as error:
                self.errorOccurred.emit(f"k: {error}")
                return False
        operands = tuple(matrix.matrix for matrix in matrices)
        try:
            check(kind, operands, scalar)
        except ValueError as error:
            self.errorOccurred.emit(str(error))
            return False
        result = None
        result_name = ""
        if kind.gives_matrix:
            result_name = next_matrix_name(matrix.name for matrix in self._document.matrices)
            result = MatrixObject(new_object_id(), result_name, compute(kind, operands, scalar))
        record = OperationRecord(
            new_object_id(),
            kind,
            tuple(matrix.name for matrix in matrices),
            operands,
            scalar,
            result_name,
            result.object_id if result is not None else None,
        )
        self._commands.execute(AddOperationCommand(record, result))
        self._animation.reset()
        return True

    # Focus -----------------------------------------------------------------------------------

    @Slot(str)
    def activate(self, object_id: str) -> None:
        if self._document.find_operation(object_id) is None:
            self.errorOccurred.emit(f"Unknown operation: {object_id!r}")
            return
        if object_id != self._document.active_operation_id:
            self._document.active_operation_id = object_id
            self._animation.reset()
            self._transformation.active_matrix_changed()

    @Slot()
    def clearFocus(self) -> None:
        if self._document.active_operation_id is not None:
            self._document.active_operation_id = None
            self._transformation.active_matrix_changed()

    @Slot(str)
    def remove(self, object_id: str) -> None:
        if self._document.find_operation(object_id) is not None:
            self._commands.execute(RemoveOperationCommand(object_id))

    @Slot()
    def removeActive(self) -> None:
        if self._document.active_operation_id:
            self.remove(self._document.active_operation_id)

    # Stepping ----------------------------------------------------------------------------------

    def _step_count(self) -> int:
        operation = self._document.active_operation
        return len(operation.derivation.steps) if operation is not None else 0

    def _go_to_step(self, index: int) -> None:
        count = self._step_count()
        if count:
            index = min(max(index, 0), count - 1)
            # The middle of the step's segment; the last step goes to the end.
            self._animation.scrub(1.0 if index == count - 1 else (index + 0.5) / count)

    @Slot()
    def nextStep(self) -> None:
        progress = self._document.animation_state.progress
        self._go_to_step(step_at(progress, self._step_count()) + 1)

    @Slot()
    def previousStep(self) -> None:
        progress = self._document.animation_state.progress
        self._go_to_step(step_at(progress, self._step_count()) - 1)

    # What the views show -------------------------------------------------------------------------

    @Property("QVariantMap", notify=viewChanged)
    def algebraView(self) -> dict:
        operation = self._document.active_operation
        if operation is not None:
            return operation_view(operation.derivation, self._document.animation_state.progress)
        active = self._document.active_matrix
        if active is None:
            return {"terms": [], "title": "No matrix", "formula": "", "history": [], "step": 0, "stepCount": 0}
        return matrix_view(active.name, active.matrix)

    def figure_scene(self) -> FigureScene | None:
        """Matrices drawn as objects, or ``None`` while the views show a plane transformation."""
        state = self._document.animation_state
        t = ease(state.progress, state.rate_function)
        operation = self._document.active_operation
        if operation is not None:
            return operation_scene(operation, t)
        active = self._document.active_matrix
        if active is not None and active.size == 3:
            return matrix_scene(active.matrix, t, active.name)
        return None

    @Property(str, notify=viewChanged)
    def figureCaption(self) -> str:
        scene = self.figure_scene()
        return scene.caption if scene is not None else ""

    @Property(bool, notify=viewChanged)
    def needs3D(self) -> bool:
        """Whether the matrices shown are 3×3 (the 2D view cannot draw them)."""
        scene = self.figure_scene()
        return scene is not None and scene.size == 3
