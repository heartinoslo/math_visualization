"""Export view model: renders the scene as an MP4 with ManimGL in a separate process."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, QUrl, Property, Signal, Slot
from PySide6.QtGui import QDesktopServices

from math_visualization.export.manim_export import (
    PROBE_CODE,
    VIDEO_EXTENSION,
    interpret_probe,
    parse_frame_count,
    render_command,
    render_config,
    render_script,
    safe_file_stem,
)
from math_visualization.export.scene_spec import (
    DEFAULT_QUALITY,
    QUALITY_PRESETS,
    build_scene_spec,
    total_frames,
)
from math_visualization.persistence.settings_store import MemorySettings, SettingsStore
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.project_viewmodel import local_path


PYTHON_KEY = "export/manimPython"
FOLDER_KEY = "export/outputFolder"
QUALITY_KEY = "export/quality"
PROBE_TIMEOUT_MS = 20_000
# Only the end of ManimGL's output is kept for error reports.
MAX_LOG_CHARACTERS = 20_000
LOG_TAIL_LINES = 25

SizeProvider = Callable[[], tuple[tuple[float, float], tuple[float, float]]]


class ExportViewModel(QObject):
    """Checks the ManimGL environment and runs one export at a time.

    The scene is captured when the export starts; editing afterwards does not
    change the video being rendered. ManimGL runs in its own process, so the
    interface stays responsive and a failing render cannot crash it.
    """

    settingsChanged = Signal()
    environmentChanged = Signal()
    stateChanged = Signal()
    progressChanged = Signal()
    statusMessage = Signal(str)
    errorOccurred = Signal(str)

    def __init__(
        self,
        document: SceneDocument,
        viewport_sizes: SizeProvider,
        settings: SettingsStore | None = None,
        default_python: str = "",
        default_folder: str = "",
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._viewport_sizes = viewport_sizes
        self._settings = settings or MemorySettings()
        self._python = self._settings.get(PYTHON_KEY, default_python)
        self._folder = self._settings.get(FOLDER_KEY, default_folder or str(Path.home() / "Videos"))
        quality = self._settings.get(QUALITY_KEY, DEFAULT_QUALITY)
        self._quality = quality if quality in QUALITY_PRESETS else DEFAULT_QUALITY
        self._environment_state = "unknown"
        self._environment_message = "Not checked yet."
        self._probe: QProcess | None = None
        self._probe_output = ""
        self._process: QProcess | None = None
        self._work_dir: str | None = None
        self._output = ""
        self._total_frames = 1
        self._progress = 0.0
        self._status = ""
        self._result_path = ""
        self._cancelled = False

    # Settings -------------------------------------------------------------------------

    @Property(str, notify=settingsChanged)
    def pythonPath(self) -> str:
        return self._python

    @Slot(str)
    def setPythonPath(self, location: str) -> None:
        path = local_path(location).strip()
        if path != self._python:
            self._python = path
            self._settings.set(PYTHON_KEY, path)
            self.settingsChanged.emit()
            self._set_environment("unknown", "Not checked yet.")

    @Property(str, notify=settingsChanged)
    def outputFolder(self) -> str:
        return self._folder

    @Property(str, notify=settingsChanged)
    def outputFolderUrl(self) -> str:
        return QUrl.fromLocalFile(self._folder).toString() if self._folder else ""

    @Slot(str)
    def setOutputFolder(self, location: str) -> None:
        path = local_path(location).strip()
        if path and path != self._folder:
            self._folder = path
            self._settings.set(FOLDER_KEY, path)
            self.settingsChanged.emit()
            self.stateChanged.emit()

    @Property("QVariantList", constant=True)
    def qualityOptions(self) -> list[dict]:
        return [{"key": preset.key, "label": preset.label} for preset in QUALITY_PRESETS.values()]

    @Property(str, notify=settingsChanged)
    def quality(self) -> str:
        return self._quality

    @Slot(str)
    def setQuality(self, key: str) -> None:
        if key not in QUALITY_PRESETS:
            self.errorOccurred.emit(f"Unknown export quality: {key!r}")
            return
        if key != self._quality:
            self._quality = key
            self._settings.set(QUALITY_KEY, key)
            self.settingsChanged.emit()
            self.stateChanged.emit()

    # Environment check ------------------------------------------------------------------

    @Property(str, notify=environmentChanged)
    def environmentState(self) -> str:
        """``unknown``, ``checking``, ``ready`` or ``missing``."""
        return self._environment_state

    @Property(str, notify=environmentChanged)
    def environmentMessage(self) -> str:
        return self._environment_message

    def _set_environment(self, state: str, message: str) -> None:
        if (state, message) != (self._environment_state, self._environment_message):
            self._environment_state, self._environment_message = state, message
            self.environmentChanged.emit()
            self.stateChanged.emit()

    @Slot()
    def checkEnvironment(self) -> None:
        """Ask the chosen Python for its ManimGL version (asynchronously)."""
        if self._probe is not None:
            return
        if not self._python:
            self._set_environment(
                "missing", "Choose the Python of your ManimGL environment (for example .venv-manim)."
            )
            return
        if not Path(self._python).is_file():
            self._set_environment("missing", f"{self._python} does not exist.")
            return
        self._set_environment("checking", "Checking ManimGL…")
        self._probe_output = ""
        probe = QProcess(self)
        probe.setProcessChannelMode(QProcess.MergedChannels)
        probe.readyReadStandardOutput.connect(
            lambda: setattr(self, "_probe_output", self._probe_output + bytes(probe.readAllStandardOutput()).decode("utf-8", "replace"))
        )
        probe.finished.connect(lambda code, _status: self._probe_finished(probe, code))
        probe.errorOccurred.connect(lambda error: self._probe_failed(probe, error))
        self._probe = probe
        QTimer.singleShot(PROBE_TIMEOUT_MS, probe, probe.kill)
        probe.start(self._python, ["-c", PROBE_CODE])

    def _probe_finished(self, probe: QProcess, exit_code: int) -> None:
        if self._probe is not probe:
            return
        self._probe = None
        status = interpret_probe(exit_code, self._probe_output)
        self._set_environment("ready" if status.ok else "missing", status.message)
        probe.deleteLater()

    def _probe_failed(self, probe: QProcess, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart and self._probe is probe:
            self._probe = None
            self._set_environment("missing", f"Could not start {self._python}.")
            probe.deleteLater()

    # Exporting ----------------------------------------------------------------------------

    @Property(bool, notify=stateChanged)
    def running(self) -> bool:
        return self._process is not None

    @Property(bool, notify=stateChanged)
    def canExport(self) -> bool:
        return self._environment_state == "ready" and self._process is None

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    @Property(str, notify=stateChanged)
    def statusText(self) -> str:
        return self._status

    @Property(str, notify=stateChanged)
    def resultPath(self) -> str:
        return self._result_path

    @Property(str, notify=stateChanged)
    def logTail(self) -> str:
        lines = self._output.replace("\r", "\n").splitlines()
        return "\n".join(line for line in lines[-LOG_TAIL_LINES:] if line.strip())

    @Property(str, notify=stateChanged)
    def fileName(self) -> str:
        """Name the next export will get (it never overwrites an earlier video)."""
        return self._target_path().name

    def _target_path(self) -> Path:
        stem = f"{safe_file_stem(self._document.title)} {self._quality}"
        candidate = Path(self._folder) / f"{stem}{VIDEO_EXTENSION}"
        counter = 2
        while candidate.exists():
            candidate = Path(self._folder) / f"{stem} ({counter}){VIDEO_EXTENSION}"
            counter += 1
        return candidate

    @Slot(result=bool)
    def startExport(self) -> bool:
        if self._process is not None:
            return False
        if self._environment_state != "ready":
            self.errorOccurred.emit("ManimGL is not ready: " + self._environment_message)
            return False
        active = self._document.active_matrix
        if self._document.active_operation_id is not None or (active is not None and active.size == 3):
            self.errorOccurred.emit(
                "Video export currently covers 2×2 transformations; select a 2×2 matrix "
                "(export of operations and 3×3 matrices comes later)"
            )
            return False
        preset = QUALITY_PRESETS[self._quality]
        size_2d, size_3d = self._viewport_sizes()
        spec = build_scene_spec(self._document, size_2d, size_3d)
        target = self._target_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            self._work_dir = tempfile.mkdtemp(prefix="math-visualization-export-")
            script = Path(self._work_dir) / "scene.py"
            config = Path(self._work_dir) / "manim.yml"
            script.write_text(render_script(spec), encoding="utf-8")
            config.write_text(render_config(preset, spec["colors"]["background"]), encoding="utf-8")
        except OSError as error:
            self._cleanup()
            self.errorOccurred.emit(f"Could not prepare the export: {error.strerror or error}")
            return False

        command = render_command(self._python, script, config, target.parent, target.stem, preset)
        process = QProcess(self)
        process.setWorkingDirectory(self._work_dir)
        process.setProcessChannelMode(QProcess.MergedChannels)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        environment.insert("PYTHONIOENCODING", "utf-8")
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(lambda: self._read_output(process))
        process.finished.connect(lambda code, status: self._export_finished(process, code, status, target))
        process.errorOccurred.connect(lambda error: self._export_error(process, error))
        self._process = process
        self._output = ""
        self._total_frames = total_frames(spec, preset)
        self._cancelled = False
        self._result_path = ""
        self._set_progress(0.0)
        self._set_status(f"Rendering {target.name}…")
        process.start(command[0], command[1:])
        return True

    @Slot()
    def cancelExport(self) -> None:
        if self._process is not None:
            self._cancelled = True
            self._process.kill()

    def _read_output(self, process: QProcess) -> None:
        text = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        self._output = (self._output + text)[-MAX_LOG_CHARACTERS:]
        frames = parse_frame_count(text)
        if frames is not None:
            self._set_progress(min(0.99, frames / self._total_frames))
        self.stateChanged.emit()

    def _export_finished(self, process: QProcess, exit_code: int, status: QProcess.ExitStatus, target: Path) -> None:
        if self._process is not process:
            return
        self._process = None
        if self._cancelled:
            self._set_status("Export cancelled.")
        elif status == QProcess.NormalExit and exit_code == 0 and target.is_file():
            self._result_path = str(target)
            self._set_progress(1.0)
            self._set_status(f"Saved {target.name}")
            self.statusMessage.emit(f"Exported {target.name}")
        else:
            self._set_status("Export failed.")
            last = self.logTail.splitlines()[-1:] or ["no output"]
            self.errorOccurred.emit(f"Manim export failed: {last[0]}")
        self._cleanup()
        process.deleteLater()

    def _export_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart and self._process is process:
            self._process = None
            self._set_status("Export failed.")
            self.errorOccurred.emit(f"Could not start {self._python}.")
            self._cleanup()
            process.deleteLater()

    def _cleanup(self) -> None:
        if self._work_dir is not None:
            shutil.rmtree(self._work_dir, ignore_errors=True)
            self._work_dir = None
        self.stateChanged.emit()

    def _set_progress(self, value: float) -> None:
        if value != self._progress:
            self._progress = value
            self.progressChanged.emit()

    def _set_status(self, text: str) -> None:
        self._status = text
        self.stateChanged.emit()

    @Slot()
    def openVideo(self) -> None:
        if self._result_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._result_path))

    @Slot()
    def openFolder(self) -> None:
        folder = os.path.dirname(self._result_path) if self._result_path else self._folder
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def shutdown(self) -> None:
        """Stop a running render when the application quits."""
        for process in (self._process, self._probe):
            if process is not None:
                process.kill()
                process.waitForFinished(2000)
        self._cleanup()
