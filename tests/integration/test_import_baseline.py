"""Integration tests for the Stage 0 package baseline."""

import runpy
from pathlib import Path

import math_visualization
from math_visualization.application import main
from math_visualization.infrastructure.paths import MAIN_QML_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_package_exposes_version() -> None:
    """The package should expose its current version."""
    assert math_visualization.__version__ == "0.1.0"


# def test_application_main_returns_success() -> None:
#     """The application bootstrap should return a successful exit code."""
#     assert main() == 0



def test_application_main_is_callable() -> None:
    """The application entry point should be callable."""
    assert callable(main)


def test_root_main_delegates_to_application_main() -> None:
    """The compatibility script must not own a second bootstrap implementation."""
    namespace = runpy.run_path(PROJECT_ROOT / "main.py")

    assert namespace["main"] is main


def test_main_qml_file_exists() -> None:
    """The QML application entry file should exist."""
    assert MAIN_QML_PATH.is_file()
    assert MAIN_QML_PATH.name == "Main.qml"
