"""Application bootstrap for Math Visualization."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from math_visualization import __version__
from math_visualization.infrastructure.exception_handler import install_exception_handler
from math_visualization.infrastructure.logging_config import configure_logging
from math_visualization.export.manim_export import default_manim_python
from math_visualization.infrastructure.paths import MAIN_QML_PATH, PROJECT_ROOT
from math_visualization.persistence import FILE_EXTENSION, RecentProjects, RecoveryStore
from math_visualization.persistence.recent_projects import SettingsStorage
from math_visualization.persistence.settings_store import QtSettings
from math_visualization.rendering.qml_types import register_qml_types
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def create_gui_application(arguments: Sequence[str] | None = None) -> QGuiApplication:
    """Create the Qt application, or return the one already owned by this process."""
    existing_application = QGuiApplication.instance()
    if existing_application is not None:
        return existing_application
    return QGuiApplication(list(arguments) if arguments is not None else sys.argv)


# Native styles (Windows, macOS) ignore the application palette and reject
# customized control parts, which breaks the dark theme. Fusion honours both
# and looks the same on every platform.
QUICK_CONTROLS_STYLE = "Fusion"
_style_configured = False


def configure_controls_style() -> None:
    """Select the Qt Quick Controls style unless QT_QUICK_CONTROLS_STYLE overrides it.

    Qt accepts a style only before QML first imports QtQuick.Controls, so this
    acts once per process; later calls (for example a second engine) do nothing.
    """
    global _style_configured
    if _style_configured:
        return
    _style_configured = True
    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle(QUICK_CONTROLS_STYLE)


def load_main_qml(
    engine: QQmlApplicationEngine,
    view_model: ApplicationViewModel,
    qml_path: Path = MAIN_QML_PATH,
    *,
    logger: logging.Logger | None = None,
) -> bool:
    """Expose ``view_model`` and load the Stage 0 QML entry document."""
    active_logger = logger or logging.getLogger(__name__)
    if not qml_path.is_file():
        active_logger.error("QML entry file does not exist: %s", qml_path)
        return False

    configure_controls_style()
    register_qml_types()
    engine.rootContext().setContextProperty("app", view_model)
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        active_logger.error("Failed to load QML entry file: %s", qml_path)
        return False

    return True


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the Math Visualization application and return its exit code."""
    logger = configure_logging()
    install_exception_handler(logger)
    application = create_gui_application(arguments)
    application.setOrganizationName("MathVisualization")
    application.setApplicationName("Math Visualization")
    application.setApplicationVersion(__version__)

    document = SceneDocument()
    recovery_directory = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    movies = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
    view_model = ApplicationViewModel(
        document,
        recent=RecentProjects(SettingsStorage(QSettings())),
        recovery=RecoveryStore(recovery_directory) if recovery_directory else None,
        settings=QtSettings(QSettings()),
        default_manim_python=default_manim_python(PROJECT_ROOT),
        default_export_folder=str(Path(movies) / "Math Visualization") if movies else "",
    )
    # A render still running when the window closes is stopped with it.
    application.aboutToQuit.connect(view_model.exporter.shutdown)
    engine = QQmlApplicationEngine()

    if not load_main_qml(engine, view_model, logger=logger):
        return 1

    # A project file given on the command line (or by "Open with") is opened at once.
    files = [argument for argument in application.arguments()[1:] if argument.lower().endswith(FILE_EXTENSION)]
    if files:
        view_model.project.openProject(files[0])

    exit_code = application.exec()

    # Destroy the QML engine first so no binding outlives the view models it reads.
    del engine

    return exit_code
