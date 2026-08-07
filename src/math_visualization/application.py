"""Application bootstrap for Math Visualization."""

from __future__ import annotations

import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from math_visualization.infrastructure.paths import MAIN_QML_PATH


def main()-> int :
    """Run the Math Visualization application."""
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Math Visualization")
    app.setApplicationVersion("0.1.0")

    if not MAIN_QML_PATH.is_file():
        print(f"{MAIN_QML_PATH} is not a file.",file=sys.stderr,)
        return 1

    engine = QQmlApplicationEngine()
    engine.load(QUrl.fromLocalFile(str(MAIN_QML_PATH)))

    if not engine.rootObjects():
        print(
            f"Failed to load QML entry file: {MAIN_QML_PATH}",
            file=sys.stderr,
        )
        return 1

    return app.exec()


    return 0