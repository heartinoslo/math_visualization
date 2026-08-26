"""Application-level view model exposed to QML."""

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.scene.scene_document import SceneDocument


class ApplicationViewModel(QObject):
    """Small Qt-facing bridge to the active :class:`SceneDocument`."""

    statusMessageChanged = Signal()

    def __init__(self, document: SceneDocument):
        super().__init__()
        self._document = document
        self._state_message = "Ready"

    @property
    def document(self) -> SceneDocument:
        """Return the single document represented by this view model."""
        return self._document

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._state_message

    @Slot()
    def ping(self) -> None:
        """Verify the QML-to-Python connection used in Stage 0."""
        self._state_message = "Python connection OK"
        self.statusMessageChanged.emit()






