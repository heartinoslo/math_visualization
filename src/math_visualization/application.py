"""Application bootstrap for Math Visualization."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from math_visualization import __version__
from math_visualization.infrastructure.exception_handler import install_exception_handler
from math_visualization.infrastructure.logging_config import configure_logging
from math_visualization.infrastructure.paths import MAIN_QML_PATH
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def create_gui_application(arguments: Sequence[str] | None = None) -> QGuiApplication:
    """Create the Qt application, or return the one already owned by this process."""
    existing_application = QGuiApplication.instance()
    if existing_application is not None:
        return existing_application
    return QGuiApplication(list(arguments) if arguments is not None else sys.argv)


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
    application.setApplicationName("Math Visualization")
    application.setApplicationVersion(__version__)

    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    engine = QQmlApplicationEngine()

    if not load_main_qml(engine, view_model, logger=logger):
        return 1

    exit_code = application.exec()

    # Destroy the QML engine first so no binding outlives the view models it reads.
    del engine

    return exit_code
