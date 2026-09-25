"""Application-level view model exposed to QML."""

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.infrastructure.logging_config import APPLICATION_LOGGER_NAME
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.animation_viewmodel import AnimationViewModel
from math_visualization.viewmodels.workspace_viewmodel import WorkspaceViewModel


THEME_MODES = ("dark", "light")

_logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.viewmodels")


class ApplicationViewModel(QObject):
    """Qt-facing root of the active :class:`SceneDocument` and its child view models."""

    statusMessageChanged = Signal()
    errorMessageChanged = Signal()
    themeModeChanged = Signal()

    def __init__(self, document: SceneDocument):
        super().__init__()
        self._document = document
        self._status_message = "Ready"
        self._error_message = ""
        self._theme_mode = "dark"
        self._workspace = WorkspaceViewModel(document, parent=self)
        self._animation = AnimationViewModel(document, parent=self)
        self._workspace.errorOccurred.connect(self.reportError)
        self._animation.errorOccurred.connect(self.reportError)

    @property
    def document(self) -> SceneDocument:
        """Return the single document represented by this view model."""
        return self._document

    @Property(QObject, constant=True)
    def workspace(self) -> WorkspaceViewModel:
        return self._workspace

    @Property(QObject, constant=True)
    def animation(self) -> AnimationViewModel:
        return self._animation

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @Slot()
    def ping(self) -> None:
        """Verify the QML-to-Python connection used in Stage 0."""
        self._status_message = "Python connection OK"
        self.statusMessageChanged.emit()

    @Slot(str)
    def reportError(self, message: str) -> None:
        """Log ``message`` and show it to the user until it is dismissed."""
        _logger.warning("%s", message)
        self._error_message = message
        self.errorMessageChanged.emit()

    @Slot()
    def clearError(self) -> None:
        if self._error_message:
            self._error_message = ""
            self.errorMessageChanged.emit()

    @Slot(str)
    def setThemeMode(self, mode: str) -> None:
        if mode not in THEME_MODES:
            self.reportError(f"Unknown theme mode: {mode!r}")
            return
        if mode != self._theme_mode:
            self._theme_mode = mode
            self.themeModeChanged.emit()

    @Slot()
    def toggleThemeMode(self) -> None:
        self.setThemeMode("light" if self._theme_mode == "dark" else "dark")
