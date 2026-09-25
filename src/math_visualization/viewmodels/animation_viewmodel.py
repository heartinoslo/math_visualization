"""Animation view model: the shared animation progress of the scene."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.scene.scene_document import SceneDocument


class AnimationViewModel(QObject):
    """Expose the document's animation progress independently of any workspace."""

    progressChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, document: SceneDocument, parent: QObject | None = None):
        super().__init__(parent)
        self._document = document

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._document.animation_state.progress

    @Slot(float)
    def setProgress(self, progress: float) -> None:
        try:
            state = replace(self._document.animation_state, progress=progress)
        except ValueError as error:
            self.errorOccurred.emit(f"Invalid animation progress: {error}")
            return
        if state != self._document.animation_state:
            self._document.animation_state = state
            self.progressChanged.emit()
