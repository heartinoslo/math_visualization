"""End-to-end coverage of the matrix algebra workbench: 3×3 matrices, operations and the Algebra view."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from test_transformation_ui import Shell

from math_visualization.math_core import Matrix2
from math_visualization.math_core.matrix3 import Matrix3


def compute_in_form(shell: Shell, kind_index: int, left: int, right: int = 0, scalar: str | None = None) -> None:
    """Fill the OPERATIONS form like a user and press Compute."""
    shell.find("operationKind").setProperty("currentIndex", kind_index)
    shell.find("operandLeft").setProperty("currentIndex", left)
    shell.find("operandRight").setProperty("currentIndex", right)
    if scalar is not None:
        shell.find("operationScalar").setProperty("text", scalar)
    shell.process()
    shell.click("computeButton")


def click_row(shell: Shell, list_name: str, row: int) -> None:
    view = shell.window.findChild(QQuickItem, list_name)
    point = view.mapToScene(QPointF(40, row * 32 + 15)).toPoint()
    QTest.mouseClick(shell.window, Qt.LeftButton, Qt.NoModifier, point)
    shell.process()


def two_matrices(shell: Shell) -> None:
    shell.click("preset_shear")
    shell.click("addMatrixButton")
    shell.type_into("matrixEntryA", "2")
    shell.type_into("matrixEntryB", "-1")


def test_3x3_matrix_is_edited_in_a_3_by_3_grid() -> None:
    shell = Shell()
    shell.click("addMatrix3Button")

    assert shell.document.active_matrix.size == 3
    shell.type_into("matrixEntryI", "4")
    assert shell.document.active_matrix.matrix == Matrix3((1, 0, 0, 0, 1, 0, 0, 0, 4))
    shell.click("preset_rotation_z")
    assert shell.document.active_matrix.matrix == Matrix3((0, -1, 0, 1, 0, 0, 0, 0, 1))
    # 2D cannot draw it and says so; the button switches to 3D.
    assert shell.find("needs3DNotice").property("visible")
    shell.click("showIn3DButton")
    assert shell.app.workspace.workspaceMode == "3d"
    assert "3×3" in shell.find("dimensionHintLabel").property("text")


def test_compute_from_the_form_and_step_through_the_algebra_view() -> None:
    shell = Shell()
    two_matrices(shell)
    # A · B is the fourth kind; operands A (row 0) and B (row 1).
    compute_in_form(shell, 3, 0, 1)

    assert [m.name for m in shell.document.matrices] == ["A", "B", "C"]
    assert shell.document.find_matrix(shell.document.active_matrix_id).matrix == (
        Matrix2(1, 1, 0, 1) @ Matrix2(2, -1, 0, 1)
    )
    assert shell.find("operationList").property("count") == 1
    assert not shell.find("visualToggles").property("enabled")

    shell.click("workspaceAlgebraTab")
    shell.process(5)
    assert shell.find("algebraTitle").property("text") == "C = A · B"
    assert shell.find("algebraStep").property("text") == "Step 1 / 4"
    shell.click("nextStepButton")
    assert shell.find("algebraStep").property("text") == "Step 2 / 4"
    assert shell.find("algebraFormula").property("text") == "c₁₂ = a₁₁·b₁₂ + a₁₂·b₂₂ = 1·(-1) + 1·1 = 0"
    shell.click("previousStepButton")
    assert shell.find("algebraStep").property("text") == "Step 1 / 4"


def test_invalid_form_input_is_reported() -> None:
    shell = Shell()
    shell.click("addMatrix3Button")
    compute_in_form(shell, 0, 0, 1)
    assert "same size" in shell.find("errorMessageLabel").property("text")
    compute_in_form(shell, 2, 0, scalar="x")
    assert "k: x is not a number" in shell.find("errorMessageLabel").property("text")


def test_focus_moves_between_operations_and_matrices() -> None:
    shell = Shell()
    two_matrices(shell)
    compute_in_form(shell, 4, 0)
    assert shell.app.operations.hasFocus

    click_row(shell, "matrixList", 0)
    assert not shell.app.operations.hasFocus
    assert shell.find("visualToggles").property("enabled")
    click_row(shell, "operationList", 0)
    assert shell.app.operations.hasFocus

    shell.click("deleteOperationButton")
    assert shell.find("operationList").property("count") == 0
    assert [m.name for m in shell.document.matrices] == ["A", "B", "C"]


def test_rendered_2d_figure_shows_the_result_columns() -> None:
    shell = Shell()
    two_matrices(shell)
    # 2 · B: B's first column (2, 0) doubles to (4, 0).
    compute_in_form(shell, 2, 1, scalar="2")
    shell.app.animation.setProgress(1.0)
    shell.process(10)
    viewport = shell.app.viewport2D

    def pixel(x, y):
        return shell.rendered_pixel("workspace2D", viewport.originX + x * 80.0, viewport.originY - y * 80.0)

    # The result's first column (green #83C167) reaches x = 4, over the grey x-axis …
    column = pixel(3.3, 0.0)
    assert column.green() > column.red() + 40 and column.green() > column.blue() + 40
    # … and the transformation layer (blue grid) is hidden: (2.5, 1.5) is background.
    background = pixel(2.5, 1.5)
    assert background.blue() < 120


def test_rendered_3d_parallelepiped() -> None:
    shell = Shell()
    if not shell.rhi_available():
        pytest.skip("Qt Quick 3D needs an RHI-based graphics API")
    shell.click("addMatrix3Button")
    shell.click("preset_scale")
    shell.app.animation.setProgress(1.0)
    shell.click("workspace3DTab")
    shell.app.viewport3D.applyPreset("top")
    shell.app.viewport3D.zoomBy(500.0)
    shell.process(10)
    view = shell.app.viewport3D.viewport()

    # Top view of diag(2, 1, 0.5): its top face covers (1.5, 0.5); the fill is yellow-tinted.
    inside = view.project((1.5, 0.5, 0.5))
    color = shell.rendered_pixel("workspace3D", inside.x, inside.y)
    assert color.red() > 60 and color.green() > 60 and color.blue() < color.red() - 20
    # The first column (green) runs along x.
    edge = view.project((1.0, 0.0, 0.0))
    green = shell.rendered_pixel("workspace3D", edge.x, edge.y)
    assert green.green() > green.red() + 30 and green.green() > green.blue() + 30


def test_duration_field_sets_seconds_per_step() -> None:
    shell = Shell()
    two_matrices(shell)
    shell.type_into("durationField", "1.5")
    assert shell.document.animation_state.duration == 1.5
    compute_in_form(shell, 3, 0, 1)
    assert shell.app.animation.totalDuration == 6.0
