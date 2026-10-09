"""End-to-end coverage of Stage 6: determinant, rank and invertibility feedback."""

from __future__ import annotations

import pytest
from test_transformation_ui import Shell, close_to

from math_visualization.math_core import Matrix2


def show(shell: Shell, preset: str) -> None:
    shell.click(f"preset_{preset}")
    shell.app.animation.setProgress(1.0)
    shell.process(10)


def is_reddish(color) -> bool:
    """RED_B blended at the square's opacity over the dark background is about (89, 54, 58)."""
    return color.red() > color.green() + 20 and color.red() > color.blue() + 15


def is_yellowish(color) -> bool:
    return color.red() > color.blue() + 25 and abs(color.red() - color.green()) < 30


def test_panel_reports_status_rank_and_inverse() -> None:
    shell = Shell()

    show(shell, "scale")
    assert shell.find("matrixStatusText").property("text") == "Invertible"
    assert shell.find("determinantValue").property("text") == "1"
    assert shell.find("orientationValue").property("text") == "Preserved"
    assert shell.find("inverseMatrix").property("visible") is True

    show(shell, "reflection")
    assert shell.find("orientationValue").property("text") == "Reversed (flipped)"

    show(shell, "projection")
    assert shell.find("matrixStatusText").property("text") == "Singular"
    assert shell.find("rankValue").property("text") == "1  (not invertible)"
    assert shell.find("noInverseText").property("visible") is True
    assert shell.find("applyInverseButton").property("enabled") is False

    shell.type_into("matrixEntryD", "0.0005")
    assert shell.find("matrixStatusText").property("text") == "Near-singular"
    assert "κ" in shell.find("matrixStatusDetail").property("text")
    assert shell.find("determinantFormulaText").property("text") == "det A = ad − bc = 1·0.0005 − 0·0 = 5e-4"


def test_apply_inverse_button_replaces_a_undoably() -> None:
    shell = Shell()
    show(shell, "scale")

    shell.click("applyInverseButton")
    assert shell.document.matrix == Matrix2(0.5, 0, 0, 2)
    assert shell.app.transformation.entryTexts == ["0.5", "0", "0", "2"]

    shell.app.scene.undo()
    assert shell.document.matrix == Matrix2(2, 0, 0, 0.5)


def test_feedback_toggles_switch_layers_in_both_views() -> None:
    shell = Shell()
    show(shell, "projection")
    assert shell.find("kernelLine").property("visible") is True
    assert shell.find("imageLine").property("visible") is True

    shell.click("toggle_show_kernel")
    assert shell.document.visual_state.show_kernel is False
    assert shell.find("kernelLine").property("visible") is False

    show(shell, "rotation")
    assert shell.find("orientationArc").property("visible") is True
    shell.click("toggle_show_orientation_arc")
    assert shell.find("orientationArc").property("visible") is False

    shell.click("workspace3DTab")
    shell.process(5)
    assert shell.find("orientationArc3D").property("visible") is False
    shell.click("toggle_show_orientation_arc")
    assert shell.find("orientationArc3D").property("visible") is True
    assert shell.find("determinantLabel3D").property("text") == "det = 1"


def test_rendered_2d_square_is_tinted_only_when_flipped() -> None:
    shell = Shell()
    show(shell, "reflection")
    viewport = shell.app.viewport2D

    def square_pixel():
        # Inside A·[0,1]² = [0,1]×[−1,0], clear of the label, arc and grid lines.
        return shell.rendered_pixel("workspace2D", viewport.originX + 0.7 * 80, viewport.originY + 0.7 * 80)

    assert is_reddish(square_pixel())
    assert shell.find("determinantLabel").property("text") == "det = -1"

    shell.click("toggle_show_flip_tint")
    shell.process(10)
    assert is_yellowish(square_pixel())


def test_rendered_2d_projection_draws_the_image_line() -> None:
    shell = Shell()
    show(shell, "projection")
    viewport = shell.app.viewport2D

    # The x-axis left of the origin: the whole plane lands on it.
    assert close_to(shell.rendered_pixel("workspace2D", viewport.originX - 2.5 * 80, viewport.originY), "#FFFF00")


def test_rendered_3d_feedback_matches_python_geometry() -> None:
    shell = Shell()
    if not shell.rhi_available():
        pytest.skip("Qt Quick 3D needs an RHI-based graphics API")
    show(shell, "singular")
    shell.click("workspace3DTab")
    shell.app.viewport3D.applyPreset("top")
    shell.process(10)
    view = shell.app.viewport3D.viewport()

    # A = [1 2; 0.5 1] squashes the plane onto span{(2, 1)}.
    point = view.project((-3.0, -1.5, 0.0))
    assert close_to(shell.rendered_pixel("workspace3D", point.x, point.y), "#FFFF00")

    show(shell, "reflection")
    point = view.project((0.7, -0.7, 0.0))
    assert is_reddish(shell.rendered_pixel("workspace3D", point.x, point.y))
