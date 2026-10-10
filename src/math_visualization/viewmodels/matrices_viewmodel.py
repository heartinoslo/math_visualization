"""Matrices view model: the list of named matrices and which one is active."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Property, Qt, Signal, Slot

from math_visualization.commands import (
    MATRIX_COMMANDS,
    OPERATION_COMMANDS,
    AddMatrixCommand,
    Command,
    CommandManager,
    RemoveMatrixCommand,
    UpdateMatrixCommand,
)
from math_visualization.math_core.matrix2 import Matrix2
from math_visualization.math_core.matrix3 import Matrix3
from math_visualization.math_core.matrix_algebra import identity
from math_visualization.scene.matrix_object import MatrixObject, new_object_id, next_matrix_name
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.formatting import format_number
from math_visualization.viewmodels.transformation_viewmodel import TransformationViewModel


def entries_text(matrix: Matrix2 | Matrix3) -> str:
    return "[" + "; ".join(" ".join(format_number(value, 2) for value in row) for row in matrix.rows) + "]"


class MatrixListModel(QAbstractListModel):
    """Read-only list model of the document's matrices for QML views."""

    ObjectIdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    EntriesTextRole = Qt.UserRole + 3
    ActiveRole = Qt.UserRole + 4
    SizeRole = Qt.UserRole + 5

    def __init__(self, document: SceneDocument, parent: QObject | None = None):
        super().__init__(parent)
        self._document = document

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._document.matrices)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._document.matrices):
            return None
        matrix = self._document.matrices[index.row()]
        if role in (Qt.DisplayRole, self.NameRole):
            return matrix.name
        if role == self.ObjectIdRole:
            return matrix.object_id
        if role == self.EntriesTextRole:
            return entries_text(matrix.matrix)
        if role == self.ActiveRole:
            return matrix.object_id == self._document.active_matrix_id
        if role == self.SizeRole:
            return matrix.size
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ObjectIdRole: QByteArray(b"objectId"),
            self.NameRole: QByteArray(b"name"),
            self.EntriesTextRole: QByteArray(b"entriesText"),
            self.ActiveRole: QByteArray(b"active"),
            self.SizeRole: QByteArray(b"size"),
        }

    def structure_changed(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def rows_changed(self) -> None:
        if self._document.matrices:
            self.dataChanged.emit(self.index(0), self.index(len(self._document.matrices) - 1))


class MatricesViewModel(QObject):
    """Adds, removes, renames and activates matrices; the active one is edited and played.

    Structural edits and renames are undoable commands. Choosing which matrix
    is active is presentation state, like selecting a vector.
    """

    matricesChanged = Signal()
    activeChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        commands: CommandManager,
        transformation: TransformationViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._commands = commands
        self._transformation = transformation
        self._model = MatrixListModel(document, self)
        self._last_active = document.active_matrix_id
        commands.add_listener(self._on_command)

    def _on_command(self, command: Command) -> None:
        if not isinstance(command, MATRIX_COMMANDS + OPERATION_COMMANDS):
            return
        if isinstance(command, UpdateMatrixCommand):
            self._model.rows_changed()
        else:
            self._model.structure_changed()
        self.matricesChanged.emit()
        self._sync_active()

    def _sync_active(self) -> None:
        if self._document.active_matrix_id != self._last_active:
            self._last_active = self._document.active_matrix_id
            self._model.rows_changed()
            self.activeChanged.emit()

    def reload(self) -> None:
        """The document was replaced (a project was opened): rebuild the list."""
        self._model.structure_changed()
        self._last_active = self._document.active_matrix_id
        self.matricesChanged.emit()
        self.activeChanged.emit()

    @Property(QObject, constant=True)
    def matrixModel(self) -> MatrixListModel:
        return self._model

    @Property(int, notify=matricesChanged)
    def matrixCount(self) -> int:
        return len(self._document.matrices)

    @Property(str, notify=activeChanged)
    def activeId(self) -> str:
        return self._document.active_matrix_id or ""

    @Slot(str)
    def activate(self, object_id: str) -> None:
        if self._document.find_matrix(object_id) is None:
            self.errorOccurred.emit(f"Unknown matrix: {object_id!r}")
            return
        if object_id != self._document.active_matrix_id or self._document.active_operation_id is not None:
            # Choosing a matrix shows that matrix, not a computed operation.
            self._document.active_matrix_id = object_id
            self._document.active_operation_id = None
            self._sync_active()
            self._transformation.active_matrix_changed()

    @Slot(result=str)
    def addMatrix(self) -> str:
        """Add the next named 2×2 matrix, the identity, and make it active."""
        return self._add(Matrix2.identity())

    @Slot(int, result=str)
    def addMatrixOfSize(self, size: int) -> str:
        if size not in (2, 3):
            self.errorOccurred.emit(f"Matrices can be 2×2 or 3×3, not {size}×{size}")
            return ""
        return self._add(identity(size))

    @Slot(result=str)
    def duplicateActive(self) -> str:
        active = self._document.active_matrix
        if active is None:
            return ""
        return self._add(active.matrix, self._document.matrix_index(active.object_id) + 1)

    def _add(self, value: Matrix2 | Matrix3, index: int | None = None) -> str:
        created = MatrixObject(
            new_object_id(), next_matrix_name(matrix.name for matrix in self._document.matrices), value
        )
        self._commands.execute(AddMatrixCommand(created, index))
        return created.object_id

    @Slot(str)
    def removeMatrix(self, object_id: str) -> None:
        if self._document.find_matrix(object_id) is not None:
            self._commands.execute(RemoveMatrixCommand(object_id))

    @Slot()
    def removeActive(self) -> None:
        if self._document.active_matrix_id:
            self.removeMatrix(self._document.active_matrix_id)

    @Slot(str, str, result=bool)
    def rename(self, object_id: str, name: str) -> bool:
        current = self._document.find_matrix(object_id)
        if current is None:
            self.errorOccurred.emit(f"Unknown matrix: {object_id!r}")
            return False
        name = name.strip()
        if any(matrix.name == name and matrix.object_id != object_id for matrix in self._document.matrices):
            self.errorOccurred.emit(f"The name {name!r} is already used")
            return False
        try:
            renamed = MatrixObject(current.object_id, name, current.matrix)
        except ValueError as error:
            self.errorOccurred.emit(f"Invalid name for {current.name}: {error}")
            return False
        if renamed != current:
            self._commands.execute(UpdateMatrixCommand(current, renamed))
        return True
