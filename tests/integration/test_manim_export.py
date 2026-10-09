"""End-to-end coverage of Stage 8: the export dialog, the environment check and real ManimGL renders.

The real-render tests need a ManimGL environment and ffmpeg. They run when
``MATH_VIS_MANIM_PYTHON`` points at that environment's Python, and are
skipped otherwise.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from test_transformation_ui import Shell, find_item

from math_visualization.export.scene_spec import HOLD_BEFORE, build_scene_spec
from math_visualization.math_core import Matrix2
from math_visualization.math_core.transformations import interpolate_from_identity
from math_visualization.viewport.viewport_3d import Viewport3D

MANIM_PYTHON = os.environ.get("MATH_VIS_MANIM_PYTHON", "")
needs_manim = pytest.mark.skipif(
    not (MANIM_PYTHON and Path(MANIM_PYTHON).is_file() and shutil.which("ffmpeg")),
    reason="set MATH_VIS_MANIM_PYTHON to a ManimGL environment (and install ffmpeg) to run real renders",
)
WIDTH, HEIGHT = 854, 480


def wait_until(shell: Shell, condition, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        shell.application.processEvents()
        time.sleep(0.02)


def open_dialog(shell: Shell):
    """Open the export dialog with its shortcut and return it."""
    QTest.keyClick(shell.window, Qt.Key_E, Qt.ControlModifier)
    shell.process(5)
    return shell.find("exportDialog")


def dialog_control(shell: Shell, name: str):
    """A control inside the export dialog (popups live outside the window's item tree)."""
    found = find_item(shell.find("exportDialog").property("contentItem"), name)
    assert found is not None, name
    return found


def check(shell: Shell, python: str) -> None:
    shell.app.exporter.setPythonPath(python)
    shell.app.exporter.checkEnvironment()
    wait_until(shell, lambda: shell.app.exporter.environmentState not in ("checking", "unknown"), 30)


# Without ManimGL ---------------------------------------------------------------------


def test_dialog_opens_from_the_menu_and_checks_the_environment() -> None:
    shell = Shell()
    dialog = open_dialog(shell)
    assert dialog.property("visible")
    # No Python chosen: the check explains what to do.
    assert shell.app.exporter.environmentState == "missing"
    assert "Choose the Python" in dialog_control(shell, "environmentMessage").property("text")
    assert not dialog_control(shell, "startExportButton").property("enabled")


def test_python_without_manimgl_is_reported(tmp_path) -> None:
    shell = Shell()
    check(shell, sys.executable)
    assert shell.app.exporter.environmentState == "missing"
    assert "not installed" in shell.app.exporter.environmentMessage

    check(shell, str(tmp_path / "no-such-python"))
    assert "does not exist" in shell.app.exporter.environmentMessage
    assert shell.app.exporter.startExport() is False
    assert "ManimGL is not ready" in shell.app.errorMessage


def test_quality_and_folder_settings(tmp_path) -> None:
    shell = Shell()
    exporter = shell.app.exporter
    open_dialog(shell)
    QMetaObject.invokeMethod(dialog_control(shell, "quality_1080p"), "click")
    shell.process()
    assert exporter.quality == "1080p"
    exporter.setOutputFolder(str(tmp_path))
    assert exporter.fileName == "Untitled 1080p.mp4"
    (tmp_path / "Untitled 1080p.mp4").write_bytes(b"")
    exporter.setOutputFolder(str(tmp_path / "x"))
    exporter.setOutputFolder(str(tmp_path))
    assert exporter.fileName == "Untitled 1080p (2).mp4"


# Real renders -------------------------------------------------------------------------


def frame_at(video: Path, seconds: float, out: Path) -> QImage:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{seconds:.3f}", "-i", str(video), "-frames:v", "1", str(out)],
        check=True,
    )
    image = QImage(str(out))
    assert (image.width(), image.height()) == (WIDTH, HEIGHT)
    return image


def near(image: QImage, x: float, y: float, test, radius: int = 3) -> bool:
    """Whether a pixel within ``radius`` of (x, y) passes ``test`` (lines are a few pixels wide)."""
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            px, py = round(x) + dx, round(y) + dy
            if 0 <= px < image.width() and 0 <= py < image.height() and test(image.pixelColor(px, py)):
                return True
    return False


def orange(color) -> bool:
    # ORANGE #FF862F, possibly anti-aliased against the dark background.
    return color.red() > 140 and 60 < color.green() < color.red() - 40 and color.blue() < 90


def yellow_fill(color) -> bool:
    # YELLOW at 30 % over #12161C is about (89, 92, 20).
    return color.red() > 60 and color.green() > 60 and color.blue() < 50


def render(shell: Shell, tmp_path: Path) -> Path:
    exporter = shell.app.exporter
    check(shell, MANIM_PYTHON)
    assert exporter.environmentState == "ready", exporter.environmentMessage
    exporter.setOutputFolder(str(tmp_path))
    assert exporter.startExport()
    assert exporter.running
    wait_until(shell, lambda: not exporter.running, 240)
    assert exporter.resultPath, exporter.logTail
    assert exporter.progress == 1.0
    return Path(exporter.resultPath)


def shear_scene(shell: Shell) -> None:
    identifier = shell.app.scene.addVector()
    shell.app.scene.setComponents(identifier, 2.0, 1.0)
    shell.app.scene.clearSelection()
    shell.click("preset_shear")
    shell.process(5)


@needs_manim
def test_2d_export_matches_the_live_geometry(tmp_path) -> None:
    shell = Shell()
    shear_scene(shell)
    spec = build_scene_spec(shell.document, shell.app.viewport2D.viewport_size, shell.app.viewport3D.viewport_size)
    video = render(shell, tmp_path)
    frame = spec["frame_2d"]
    scale = HEIGHT / frame["height"]

    def pixel(x, y):
        return (WIDTH / 2 + (x - frame["center"][0]) * scale, HEIGHT / 2 - (y - frame["center"][1]) * scale)

    # Halfway through the smooth animation t = smooth(0.5) = 0.5, at the end t = 1.
    for seconds, t in ((HOLD_BEFORE + 1.0, 0.5), (HOLD_BEFORE + 2.0 + 0.9, 1.0)):
        image = frame_at(video, seconds, tmp_path / f"frame{t}.png")
        current = interpolate_from_identity(Matrix2(1, 1, 0, 1), t)
        tip = current.apply_point(2.0, 1.0)
        assert near(image, *pixel(0.85 * tip[0], 0.85 * tip[1]), orange), f"vector at t={t}"
        assert near(image, *pixel(*current.apply_point(0.8, 0.2)), yellow_fill), f"square at t={t}"


@needs_manim
def test_3d_export_matches_the_live_camera(tmp_path) -> None:
    shell = Shell()
    shear_scene(shell)
    shell.app.workspace.setWorkspaceMode("3d")
    shell.app.viewport3D.zoomBy(600.0)
    shell.process(5)
    video = render(shell, tmp_path)
    view = Viewport3D(shell.document.workspace_state_3d, WIDTH, HEIGHT)
    image = frame_at(video, HOLD_BEFORE + 2.0 + 0.9, tmp_path / "end3d.png")

    tip = view.project((0.85 * 3.0, 0.85 * 1.0, 0.0))
    square = view.project((1.0, 0.25, 0.0))
    assert near(image, tip.x, tip.y, orange)
    assert near(image, square.x, square.y, yellow_fill)


@needs_manim
def test_cancel_stops_the_render_without_a_result(tmp_path) -> None:
    shell = Shell()
    shear_scene(shell)
    exporter = shell.app.exporter
    check(shell, MANIM_PYTHON)
    exporter.setOutputFolder(str(tmp_path))
    exporter.setQuality("1080p")
    assert exporter.startExport()
    shell.process(5)
    exporter.cancelExport()
    wait_until(shell, lambda: not exporter.running, 30)

    assert exporter.statusText == "Export cancelled."
    assert exporter.resultPath == ""
    # The interface is still usable afterwards.
    shell.click("preset_rotation")
    assert shell.document.matrix == Matrix2(0, -1, 1, 0)
