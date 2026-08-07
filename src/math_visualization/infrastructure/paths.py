"""Centralized filesystem paths for Math Visualization."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

QML_DIRECTORY = PROJECT_ROOT / "qml"
MAIN_QML_PATH = QML_DIRECTORY / "Main.qml"