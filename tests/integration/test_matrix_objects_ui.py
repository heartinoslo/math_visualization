"""End-to-end coverage of named matrices: the list, renaming, deleting and what the canvas shows."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from test_transformation_ui import Shell, close_to

from math_visualization.math_core import Matrix2


def click_matrix_row(shell: Shell, row: int) -> None:
    matrix_list = shell.window.findChild(QQuickItem, "matrixList")
    point = matrix_list.mapToScene(QPointF(40, row * 32 + 15)).toPoint()
    QTest.mouseClick(shell.window, Qt.LeftButton, Qt.NoModifier, point)
    shell.process()


def test_add_and_switch_matrices_from_the_list() -> None:
    shell = Shell()
    shell.click("addMatrixButton")
    assert shell.find("matrixNameField").property("text") == "B"
    shell.click("preset_rotation")

    click_matrix_row(shell, 0)
    assert shell.find("matrixNameField").property("text") == "A"
    assert shell.find("matrixEntryB").property("text") == "0"
    click_matrix_row(shell, 1)
    assert shell.find("matrixEntryB").property("text") == "-1"
    assert shell.find("targetMatrixText").property("text") == "B = [ 0  -1 ; 1  0 ]"


def test_renaming_the_active_matrix() -> None:
    shell = Shell()
    shell.type_into("matrixNameField", "Rot")
    assert shell.document.active_matrix.name == "Rot"
    assert shell.find("determinantFormulaText").property("text").startswith("det Rot")
    assert shell.find("undoAction").property("text") == "Undo Rename A"


def test_deleting_every_matrix_leaves_the_identity() -> None:
    shell = Shell()
    shell.click("preset_shear")
    shell.click("deleteMatrixButton")

    assert shell.document.matrices == []
    assert shell.find("noMatrixHint").property("visible")
    assert shell.find("noMatricesHint").property("visible")
    assert not shell.find("matrixEditor").property("enabled")
    assert not shell.find("deleteMatrixButton").property("enabled")

    shell.click("addMatrixButton")
    assert shell.find("matrixEditor").property("enabled")
    assert shell.document.active_matrix.name == "A"


def test_canvas_follows_the_active_matrix() -> None:
    shell = Shell()
    shell.click("preset_shear")
    shell.click("addMatrixButton")
    shell.app.animation.setProgress(1.0)
    shell.process(10)
    viewport = shell.app.viewport2D

    def pixel(x, y):
        return shell.rendered_pixel("workspace2D", viewport.originX + x * 80.0, viewport.originY - y * 80.0)

    # B is the identity: ĵ points straight up.
    assert close_to(pixel(0.0, 0.6), "#FC6255")
    click_matrix_row(shell, 0)
    shell.process(10)
    # A is the shear: ĵ goes to (1, 1).
    assert close_to(pixel(0.5, 0.5), "#FC6255")
    assert shell.document.matrix == Matrix2(1, 1, 0, 1)
