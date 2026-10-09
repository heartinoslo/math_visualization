"""Application-level view model exposed to QML."""

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.commands import CommandManager
from math_visualization.persistence import RecentProjects, RecoveryStore
from math_visualization.infrastructure.logging_config import APPLICATION_LOGGER_NAME
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.animation_viewmodel import AnimationViewModel
from math_visualization.viewmodels.inspector_viewmodel import InspectorViewModel
from math_visualization.viewmodels.matrix_properties_viewmodel import MatrixPropertiesViewModel
from math_visualization.viewmodels.project_viewmodel import ProjectViewModel
from math_visualization.viewmodels.scene_objects_viewmodel import SceneObjectsViewModel
from math_visualization.viewmodels.transformation_viewmodel import TransformationViewModel
from math_visualization.viewmodels.viewport2d_viewmodel import Viewport2DViewModel
from math_visualization.viewmodels.viewport3d_viewmodel import Viewport3DViewModel
from math_visualization.viewmodels.workspace_viewmodel import WorkspaceViewModel


THEME_MODES = ("dark", "light")

_logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.viewmodels")


class ApplicationViewModel(QObject):
    """Qt-facing root of the active :class:`SceneDocument` and its child view models."""

    statusMessageChanged = Signal()
    errorMessageChanged = Signal()
    themeModeChanged = Signal()

    def __init__(
        self,
        document: SceneDocument,
        recent: RecentProjects | None = None,
        recovery: RecoveryStore | None = None,
    ):
        """``recent`` and ``recovery`` default to in-memory / disabled, so tests
        never touch the user's settings; :func:`application.main` passes real ones."""
        super().__init__()
        self._document = document
        self._status_message = "Ready"
        self._error_message = ""
        self._theme_mode = "dark"
        self._workspace = WorkspaceViewModel(document, parent=self)
        self._animation = AnimationViewModel(document, parent=self)
        # One history for every undoable edit (vectors and the matrix).
        self._commands = CommandManager(document)
        self._scene = SceneObjectsViewModel(document, self._commands, parent=self)
        self._inspector = InspectorViewModel(self._scene, parent=self)
        self._transformation = TransformationViewModel(
            document, self._commands, self._animation, self._scene, parent=self
        )
        self._matrix_properties = MatrixPropertiesViewModel(document, self._transformation, parent=self)
        self._viewport_2d = Viewport2DViewModel(
            document, self._workspace, self._scene, self._transformation, parent=self
        )
        self._viewport_3d = Viewport3DViewModel(
            document, self._workspace, self._scene, self._transformation, parent=self
        )
        self._project = ProjectViewModel(
            document, self._commands, self.replace_document, recent, recovery, parent=self
        )
        self._project.statusMessage.connect(self._set_status_message)
        self._transformation.visualStateChanged.connect(self._project.refresh_dirty)
        self._animation.settingsChanged.connect(self._project.refresh_dirty)
        for child in (
            self._project,
            self._workspace,
            self._animation,
            self._scene,
            self._inspector,
            self._transformation,
            self._matrix_properties,
            self._viewport_3d,
        ):
            child.errorOccurred.connect(self.reportError)

    @property
    def document(self) -> SceneDocument:
        """Return the single document represented by this view model."""
        return self._document

    def replace_document(self, document: SceneDocument) -> None:
        """Show ``document`` instead of the current one, with a fresh history.

        The document object is shared by every view model, so it is updated in
        place and each view model then publishes its state again.
        """
        self._animation.pause()
        self._scene.endDrag()
        self._document.replace_contents(document)
        self._commands.clear()
        self.clearError()
        for child in (self._animation, self._scene, self._transformation, self._workspace):
            child.reload()

    @Property(QObject, constant=True)
    def project(self) -> ProjectViewModel:
        return self._project

    @Property(QObject, constant=True)
    def workspace(self) -> WorkspaceViewModel:
        return self._workspace

    @Property(QObject, constant=True)
    def animation(self) -> AnimationViewModel:
        return self._animation

    @Property(QObject, constant=True)
    def scene(self) -> SceneObjectsViewModel:
        return self._scene

    @Property(QObject, constant=True)
    def inspector(self) -> InspectorViewModel:
        return self._inspector

    @Property(QObject, constant=True)
    def transformation(self) -> TransformationViewModel:
        return self._transformation

    @Property(QObject, constant=True)
    def matrixProperties(self) -> MatrixPropertiesViewModel:
        return self._matrix_properties

    @Property(QObject, constant=True)
    def viewport2D(self) -> Viewport2DViewModel:
        return self._viewport_2d

    @Property(QObject, constant=True)
    def viewport3D(self) -> Viewport3DViewModel:
        return self._viewport_3d

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    def _set_status_message(self, message: str) -> None:
        if message != self._status_message:
            self._status_message = message
            self.statusMessageChanged.emit()

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
