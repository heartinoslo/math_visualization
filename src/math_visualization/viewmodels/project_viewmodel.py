"""Project view model: new / open / save, unsaved changes, undo and redo, recovery."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Property, Signal, Slot

from math_visualization.commands import Command, CommandManager
from math_visualization.infrastructure.logging_config import APPLICATION_LOGGER_NAME
from math_visualization.persistence import (
    FILE_EXTENSION,
    ProjectFileError,
    RecentProjects,
    RecoveryStore,
    read_project,
    write_project,
)
from math_visualization.scene.scene_document import SceneDocument


APPLICATION_TITLE = "Math Visualization"
UNTITLED = "Untitled"
# While there are unsaved changes, a recovery snapshot is written this often.
AUTOSAVE_INTERVAL_MS = 60_000

_logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.project")


def local_path(location: str) -> str:
    """Accept a plain path or a ``file:`` URL (what QML file dialogs return)."""
    if location.startswith("file:"):
        return QUrl(location).toLocalFile()
    return location


class ProjectViewModel(QObject):
    """Owns the project file of the single open document.

    "Dirty" means the document differs from what was last saved: an undoable
    edit (vectors, matrix) or a saved display setting (visual options, rate
    function, playback speed) changed. The camera, playback position,
    selection and workspace mode are saved too, but moving them alone does
    not count as an unsaved change.
    """

    fileChanged = Signal()
    dirtyChanged = Signal()
    historyChanged = Signal()
    recentProjectsChanged = Signal()
    recoveryChanged = Signal()
    statusMessage = Signal(str)
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        commands: CommandManager,
        replace_document: Callable[[SceneDocument], None],
        recent: RecentProjects | None = None,
        recovery: RecoveryStore | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._commands = commands
        self._replace_document = replace_document
        self._recent = recent or RecentProjects()
        self._recovery = recovery
        self._file_path = ""
        self._forced_dirty = False
        self._saved_settings = self._settings()
        self._dirty = False
        self._recovery_available = recovery is not None and recovery.exists()
        commands.add_listener(self._on_command)
        self._autosave = QTimer(self)
        self._autosave.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave.timeout.connect(self.writeRecoverySnapshot)
        if recovery is not None:
            self._autosave.start()

    # Dirty state ------------------------------------------------------------------------

    def _settings(self) -> tuple:
        """The saved display settings whose change counts as an unsaved edit."""
        animation = self._document.animation_state
        return (self._document.visual_state, animation.rate_function, animation.playback_speed, animation.duration)

    def refresh_dirty(self) -> None:
        dirty = self._forced_dirty or not self._commands.is_clean or self._settings() != self._saved_settings
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirtyChanged.emit()

    def _on_command(self, _command: Command) -> None:
        self.historyChanged.emit()
        self.refresh_dirty()

    def _mark_saved(self) -> None:
        self._commands.mark_clean()
        self._forced_dirty = False
        self._saved_settings = self._settings()
        self.refresh_dirty()

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    # File identity ----------------------------------------------------------------------

    @Property(str, notify=fileChanged)
    def filePath(self) -> str:
        return self._file_path

    @Property(bool, notify=fileChanged)
    def hasFilePath(self) -> bool:
        return bool(self._file_path)

    @Property(str, notify=fileChanged)
    def displayName(self) -> str:
        return Path(self._file_path).stem if self._file_path else UNTITLED

    @Property(str, notify=fileChanged)
    def suggestedFileName(self) -> str:
        return self.displayName + FILE_EXTENSION

    @Property(str, notify=fileChanged)
    def folder(self) -> str:
        """Folder of the current file as a URL, for file dialogs; empty when untitled."""
        if not self._file_path:
            return ""
        return QUrl.fromLocalFile(str(Path(self._file_path).parent)).toString()

    @Property(str, notify=dirtyChanged)
    def windowTitle(self) -> str:
        marker = "*" if self._dirty else ""
        return f"{self.displayName}{marker} — {APPLICATION_TITLE}"

    @Property("QStringList", constant=True)
    def nameFilters(self) -> list[str]:
        return [f"Math Visualization scenes (*{FILE_EXTENSION})", "All files (*)"]

    def _set_file_path(self, path: str) -> None:
        if path != self._file_path:
            self._file_path = path
            self.fileChanged.emit()
            self.dirtyChanged.emit()

    # New / open / save ----------------------------------------------------------------

    @Slot()
    def newProject(self) -> None:
        """Start an empty untitled project. QML asks about unsaved changes first."""
        self._replace_document(SceneDocument())
        self._set_file_path("")
        self._mark_saved()
        self._discard_recovery()
        self.statusMessage.emit("New project")

    @Slot(str, result=bool)
    def openProject(self, location: str) -> bool:
        path = local_path(location)
        try:
            document = read_project(path)
        except ProjectFileError as error:
            if not os.path.exists(path):
                self._recent.remove(path)
                self.recentProjectsChanged.emit()
            self.errorOccurred.emit(str(error))
            return False
        self._replace_document(document)
        self._set_file_path(os.path.abspath(path))
        self._mark_saved()
        self._discard_recovery()
        self._remember(path)
        self.statusMessage.emit(f"Opened {Path(path).name}")
        return True

    @Slot(result=bool)
    def saveProject(self) -> bool:
        """Save to the current file; returns False when there is none yet (QML then asks where)."""
        if not self._file_path:
            return False
        return self._write(self._file_path)

    @Slot(str, result=bool)
    def saveProjectAs(self, location: str) -> bool:
        path = local_path(location)
        if not path:
            return False
        if Path(path).suffix.lower() != FILE_EXTENSION:
            path += FILE_EXTENSION
        return self._write(os.path.abspath(path))

    def _write(self, path: str) -> bool:
        self._document.title = Path(path).stem
        try:
            write_project(self._document, path)
        except ProjectFileError as error:
            self.errorOccurred.emit(str(error))
            return False
        self._set_file_path(path)
        self._mark_saved()
        self._discard_recovery()
        self._remember(path)
        self.statusMessage.emit(f"Saved {Path(path).name}")
        return True

    # Recent projects ---------------------------------------------------------------------

    def _remember(self, path: str) -> None:
        self._recent.add(path)
        self.recentProjectsChanged.emit()

    @Property("QVariantList", notify=recentProjectsChanged)
    def recentProjects(self) -> list[dict]:
        return [
            {"path": path, "name": Path(path).name, "folder": str(Path(path).parent)}
            for path in self._recent.paths()
        ]

    @Slot()
    def clearRecentProjects(self) -> None:
        self._recent.clear()
        self.recentProjectsChanged.emit()

    # Undo and redo -----------------------------------------------------------------------

    @Property(bool, notify=historyChanged)
    def canUndo(self) -> bool:
        return self._commands.can_undo

    @Property(bool, notify=historyChanged)
    def canRedo(self) -> bool:
        return self._commands.can_redo

    @Property(str, notify=historyChanged)
    def undoText(self) -> str:
        label = self._commands.undo_label
        return f"Undo {label}" if label else "Undo"

    @Property(str, notify=historyChanged)
    def redoText(self) -> str:
        label = self._commands.redo_label
        return f"Redo {label}" if label else "Redo"

    @Slot(result=bool)
    def undo(self) -> bool:
        return self._commands.undo()

    @Slot(result=bool)
    def redo(self) -> bool:
        return self._commands.redo()

    # Crash recovery ----------------------------------------------------------------------

    @Property(bool, notify=recoveryChanged)
    def recoveryAvailable(self) -> bool:
        return self._recovery_available

    @Slot()
    def writeRecoverySnapshot(self) -> None:
        """Called by the autosave timer: keep a copy of unsaved work."""
        if self._recovery is None or not self._dirty or self._recovery_available:
            return
        try:
            self._recovery.write(self._document, self._file_path or None)
        except ProjectFileError as error:
            _logger.warning("Recovery snapshot failed: %s", error)

    @Slot(result=bool)
    def restoreRecovery(self) -> bool:
        if self._recovery is None or not self._recovery_available:
            return False
        try:
            recovered = self._recovery.read()
        except ProjectFileError as error:
            self.errorOccurred.emit(str(error))
            self.discardRecovery()
            return False
        self._replace_document(recovered.document)
        self._set_file_path(recovered.original_path or "")
        self._mark_saved()
        # Restored work has never been saved: keep it marked until it is.
        self._forced_dirty = True
        self.refresh_dirty()
        self._set_recovery_available(False)
        self.statusMessage.emit("Recovered unsaved work")
        return True

    @Slot()
    def discardRecovery(self) -> None:
        self._discard_recovery()

    def _discard_recovery(self) -> None:
        if self._recovery is not None:
            self._recovery.discard()
        self._set_recovery_available(False)

    def _set_recovery_available(self, available: bool) -> None:
        if available != self._recovery_available:
            self._recovery_available = available
            self.recoveryChanged.emit()

    @Slot()
    def prepareToQuit(self) -> None:
        """The user is closing with nothing to keep (saved, or changes discarded)."""
        self._autosave.stop()
        if not self._recovery_available:
            self._discard_recovery()
