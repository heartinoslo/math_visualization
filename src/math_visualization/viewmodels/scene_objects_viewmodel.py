"""Scene objects view model: the vector list, selection and every vector edit."""

from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Property,
    Qt,
    Signal,
    Slot,
)

from math_visualization.commands import (
    AddVectorCommand,
    Command,
    CommandManager,
    RemoveVectorCommand,
    UpdateVectorCommand,
)
from math_visualization.math_core import Vector2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import (
    VectorObject,
    new_object_id,
    next_vector_color,
    next_vector_name,
)
from math_visualization.viewmodels.formatting import format_number


DEFAULT_NEW_VECTOR = Vector2(1.0, 1.0)
VECTOR_COMMANDS = (AddVectorCommand, RemoveVectorCommand, UpdateVectorCommand)


class VectorListModel(QAbstractListModel):
    """Read-only list model of the document's vectors for QML views."""

    ObjectIdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    ColorRole = Qt.UserRole + 3
    ComponentsTextRole = Qt.UserRole + 4
    SelectedRole = Qt.UserRole + 5

    def __init__(self, document: SceneDocument, parent: QObject | None = None):
        super().__init__(parent)
        self._document = document

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._document.vectors)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._document.vectors):
            return None
        vector = self._document.vectors[index.row()]
        if role in (Qt.DisplayRole, self.NameRole):
            return vector.name
        if role == self.ObjectIdRole:
            return vector.object_id
        if role == self.ColorRole:
            return vector.color
        if role == self.ComponentsTextRole:
            return f"({format_number(vector.vector.x)}, {format_number(vector.vector.y)})"
        if role == self.SelectedRole:
            return vector.object_id == self._document.selected_object_id
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ObjectIdRole: QByteArray(b"objectId"),
            self.NameRole: QByteArray(b"name"),
            # Not "color": a delegate's own colour property would shadow it.
            self.ColorRole: QByteArray(b"vectorColor"),
            self.ComponentsTextRole: QByteArray(b"componentsText"),
            self.SelectedRole: QByteArray(b"selected"),
        }

    def structure_changed(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def rows_changed(self) -> None:
        if self._document.vectors:
            self.dataChanged.emit(self.index(0), self.index(len(self._document.vectors) - 1))


class SceneObjectsViewModel(QObject):
    """Owns the command manager; every vector edit in the application goes through it.

    Selection is presentation state stored in the document; it is not an
    undoable edit, so it is changed directly.
    """

    vectorsChanged = Signal()
    selectionChanged = Signal()
    historyChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        commands: CommandManager | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._model = VectorListModel(document, self)
        self._commands = commands or CommandManager(document)
        self._commands.add_listener(self._on_command)
        self._drag_key: str | None = None
        self._drag_id: str | None = None
        self._last_selection = document.selected_object_id

    # Observation ------------------------------------------------------------

    def _on_command(self, command: Command) -> None:
        self.historyChanged.emit()
        if not isinstance(command, VECTOR_COMMANDS):
            return
        if isinstance(command, UpdateVectorCommand):
            self._model.rows_changed()
        else:
            self._model.structure_changed()
        self.vectorsChanged.emit()
        self._sync_selection()

    def _sync_selection(self) -> None:
        current = self._document.selected_object_id
        if current != self._last_selection:
            self._last_selection = current
            self._model.rows_changed()
            self.selectionChanged.emit()

    @property
    def document(self) -> SceneDocument:
        return self._document

    @property
    def commands(self) -> CommandManager:
        return self._commands

    @property
    def selected_vector(self) -> VectorObject | None:
        return self._document.find_vector(self._document.selected_object_id)

    @Property(QObject, constant=True)
    def vectorModel(self) -> VectorListModel:
        return self._model

    @Property(int, notify=vectorsChanged)
    def vectorCount(self) -> int:
        return len(self._document.vectors)

    @Property(str, notify=selectionChanged)
    def selectedId(self) -> str:
        return self._document.selected_object_id or ""

    @Property(bool, notify=historyChanged)
    def canUndo(self) -> bool:
        return self._commands.can_undo

    @Property(bool, notify=historyChanged)
    def canRedo(self) -> bool:
        return self._commands.can_redo

    # Selection --------------------------------------------------------------

    @Slot(str)
    def select(self, object_id: str) -> None:
        if object_id and self._document.find_vector(object_id) is None:
            self.errorOccurred.emit(f"Unknown object: {object_id!r}")
            return
        self._document.selected_object_id = object_id or None
        self._sync_selection()

    @Slot()
    def clearSelection(self) -> None:
        self.select("")

    # Structure --------------------------------------------------------------

    @Slot(result=str)
    def addVector(self) -> str:
        """Create the next named vector at (1, 1), select it and return its id."""
        return self._add(DEFAULT_NEW_VECTOR)

    @Slot(result=str)
    def duplicateSelected(self) -> str:
        source = self.selected_vector
        if source is None:
            return ""
        index = self._document.vector_index(source.object_id) + 1
        return self._add(source.vector, index)

    def _add(self, value: Vector2, index: int | None = None) -> str:
        vectors = self._document.vectors
        created = VectorObject(
            object_id=new_object_id(),
            name=next_vector_name(vector.name for vector in vectors),
            color=next_vector_color(vector.color for vector in vectors),
            vector=value,
        )
        self._commands.execute(AddVectorCommand(created, index))
        return created.object_id

    @Slot()
    def removeSelected(self) -> None:
        if self._document.selected_object_id:
            self.removeVector(self._document.selected_object_id)

    @Slot(str)
    def removeVector(self, object_id: str) -> None:
        if self._document.find_vector(object_id) is None:
            return
        self._commands.execute(RemoveVectorCommand(object_id))

    # Edits ------------------------------------------------------------------

    def _update(self, object_id: str, merge_key: str | None = None, **changes) -> bool:
        current = self._document.find_vector(object_id)
        if current is None:
            self.errorOccurred.emit(f"Unknown object: {object_id!r}")
            return False
        try:
            updated = VectorObject(
                object_id=current.object_id,
                name=changes.get("name", current.name),
                color=changes.get("color", current.color),
                vector=changes.get("vector", current.vector),
            )
        except (TypeError, ValueError) as error:
            self.errorOccurred.emit(f"Invalid value for {current.name}: {error}")
            return False
        if updated != current:
            self._commands.execute(UpdateVectorCommand(current, updated, merge_key))
        return True

    @Slot(str, float, float, result=bool)
    def setComponents(self, object_id: str, x: float, y: float) -> bool:
        try:
            value = Vector2(x, y)
        except (TypeError, ValueError) as error:
            self.errorOccurred.emit(f"Invalid components: {error}")
            return False
        return self._update(object_id, vector=value)

    @Slot(str, str, result=bool)
    def rename(self, object_id: str, name: str) -> bool:
        name = name.strip()
        if any(
            vector.name == name and vector.object_id != object_id
            for vector in self._document.vectors
        ):
            self.errorOccurred.emit(f"The name {name!r} is already used")
            return False
        return self._update(object_id, name=name)

    @Slot(str, str, result=bool)
    def setColor(self, object_id: str, color: str) -> bool:
        return self._update(object_id, color=color)

    # Dragging (mathematical coordinates; viewports convert pointer positions) ---

    @Slot(str, result=bool)
    def beginDrag(self, object_id: str) -> bool:
        if self._document.find_vector(object_id) is None:
            return False
        self._drag_id = object_id
        self._drag_key = uuid4().hex
        self.select(object_id)
        return True

    @Slot(float, float)
    def dragTo(self, x: float, y: float) -> None:
        if self._drag_id is None:
            return
        try:
            value = Vector2(x, y)
        except (TypeError, ValueError):
            return
        self._update(self._drag_id, merge_key=self._drag_key, vector=value)

    @Slot()
    def endDrag(self) -> None:
        self._drag_id = None
        self._drag_key = None

    @property
    def dragging(self) -> bool:
        return self._drag_id is not None

    # History (exposed for Stage 7's undo/redo UI) ------------------------------

    @Slot(result=bool)
    def undo(self) -> bool:
        return self._commands.undo()

    @Slot(result=bool)
    def redo(self) -> bool:
        return self._commands.redo()
