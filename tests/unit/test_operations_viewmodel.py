"""Tests for computing operations, the algebra view, the figures and 3×3 editing."""

import pytest

from math_visualization.math_core import Matrix2
from math_visualization.math_core.matrix3 import Matrix3
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.algebra_view import step_at
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def make_app():
    document = SceneDocument()
    app = ApplicationViewModel(document)
    app.viewport2D.setViewportSize(800.0, 600.0)
    app.viewport3D.setViewportSize(900.0, 600.0)
    return document, app


def two_matrices(app, first="shear", second="rotation"):
    a = app.document.active_matrix_id
    app.transformation.applyPreset(first)
    b = app.matrices.addMatrix()
    app.transformation.applyPreset(second)
    return a, b


def test_compute_creates_the_result_and_focuses_the_operation() -> None:
    document, app = make_app()
    a, b = two_matrices(app)

    assert app.operations.compute("multiply", a, b, "")
    assert [m.name for m in document.matrices] == ["A", "B", "C"]
    assert document.find_matrix(document.active_matrix_id).matrix == Matrix2(1, 1, 0, 1) @ Matrix2(0, -1, 1, 0)
    assert app.operations.hasFocus and app.operations.operationCount == 1
    assert app.project.undoText == "Undo Compute C = A · B"
    # The views now explain the operation instead of playing a transformation.
    assert not app.transformation.showsTransformation
    assert app.animation.segments == 4 and app.animation.progress == 0.0

    app.project.undo()
    assert [m.name for m in document.matrices] == ["A", "B"] and not app.operations.hasFocus


@pytest.mark.parametrize(
    ("kind", "right", "scalar", "message"),
    [("add", "3x3", "", "same size"), ("scale", None, "two", "k: two is not a number"), ("multiply", "missing", "", "needs 2")],
)
def test_invalid_operations_are_explained(kind, right, scalar, message) -> None:
    document, app = make_app()
    a = document.active_matrix_id
    right_id = {"3x3": None, "missing": "nope", None: ""}[right]
    if right == "3x3":
        right_id = app.matrices.addMatrixOfSize(3)
    assert not app.operations.compute(kind, a, right_id, scalar)
    assert message in app.errorMessage


def test_algebra_view_walks_through_the_steps() -> None:
    document, app = make_app()
    a, b = two_matrices(app)
    app.operations.compute("add", a, b, "")
    operations = app.operations

    view = operations.algebraView
    assert view["title"] == "C = A + B" and view["step"] == 1 and view["stepCount"] == 4
    result = view["terms"][-1]
    assert [cell["state"] for cell in result["cells"]] == ["active", "hidden", "hidden", "hidden"]
    assert [cell["text"] for cell in result["cells"]][:2] == ["1", "?"]

    operations.nextStep()
    operations.nextStep()
    view = operations.algebraView
    assert view["step"] == 3 and len(view["history"]) == 2
    assert view["formula"] == "c₂₁ = a₂₁ + b₂₁ = 0 + 1 = 1"
    operations.nextStep()
    operations.nextStep()
    assert operations.algebraView["step"] == 4 and app.animation.progress == 1.0
    assert all(cell["state"] != "hidden" for cell in operations.algebraView["terms"][-1]["cells"])
    operations.previousStep()
    assert operations.algebraView["step"] == 3 and not app.animation.playing


def test_step_boundaries() -> None:
    assert [step_at(p, 4) for p in (0.0, 0.24, 0.25, 0.99, 1.0)] == [0, 0, 1, 3, 3]


def test_determinant_view_reveals_the_value_at_the_end() -> None:
    document, app = make_app()
    m = app.matrices.addMatrixOfSize(3)
    app.transformation.applyPreset("shear")
    app.operations.compute("determinant", m, "", "")

    view = app.operations.algebraView
    assert view["terms"][-1] == {"type": "number", "text": "?"}
    first = view["terms"][1]["cells"]
    assert first[0]["state"] == "pivot" and first[4]["state"] == "minor" and first[1]["state"] == "dim"
    app.animation.setProgress(1.0)
    assert app.operations.algebraView["terms"][-1]["text"] == "1"
    # det produces no new matrix.
    assert [mat.name for mat in document.matrices] == ["A", "B"]


def test_selecting_a_matrix_leaves_the_operation_view() -> None:
    document, app = make_app()
    a, b = two_matrices(app)
    app.operations.compute("transpose", a, "", "")
    assert app.operations.hasFocus

    app.matrices.activate(a)
    assert not app.operations.hasFocus and app.transformation.showsTransformation
    assert app.animation.segments == 1
    op_id = document.operations[0].object_id
    app.operations.activate(op_id)
    assert app.operations.hasFocus and app.animation.segments == 4


def test_figures_follow_playback_in_both_views() -> None:
    document, app = make_app()
    a, b = two_matrices(app, "scale", "identity")
    app.operations.compute("scale", a, "", "3")

    app.animation.setRateFunction("linear")
    app.animation.setProgress(0.5)
    shapes = app.viewport2D.figureShapes
    assert shapes["visible"] and not shapes["needs3D"]
    result = [arrow for arrow in shapes["arrows"] if arrow["role"] == "result"]
    # Halfway, columns of 2·A: (2·2, 0) on screen is 4 units right of the origin.
    assert result[0]["x2"] - result[0]["x1"] == pytest.approx(4 * 80.0)
    figures = app.viewport3D.figures
    assert figures["visible"] and len(figures["resultFill"]) == 2 * 9


def test_3x3_matrices_are_edited_and_shown_in_3d() -> None:
    document, app = make_app()
    m = app.matrices.addMatrixOfSize(3)
    assert app.transformation.matrixSize == 3 and len(app.transformation.entryTexts) == 9
    assert [p["key"] for p in app.transformation.presets][:3] == ["identity", "scale", "rotation_z"]

    assert app.transformation.setEntryText(8, "4")
    assert document.find_matrix(m).matrix == Matrix3((1, 0, 0, 0, 1, 0, 0, 0, 4))
    assert app.transformation.targetText == "B = [ 1  0  0 ; 0  1  0 ; 0  0  4 ]"
    assert app.matrixProperties.size == 3 and app.matrixProperties.determinantText == "4"
    assert app.matrixProperties.inverseEntryTexts[-1] == "0.25"
    assert app.operations.needs3D and app.viewport2D.figureShapes["needs3D"]
    assert len(app.viewport3D.figures["arrows"]) == 6


def test_3x3_singular_status_speaks_of_space() -> None:
    _, app = make_app()
    app.matrices.addMatrixOfSize(3)
    app.transformation.applyPreset("projection")
    assert app.matrixProperties.statusText == "Singular"
    assert app.matrixProperties.statusDetail.startswith("Space collapses onto a plane")


def test_step_duration_is_settable_and_scales_with_steps() -> None:
    document, app = make_app()
    a, b = two_matrices(app)
    app.animation.setDuration(1.5)
    app.operations.compute("multiply", a, b, "")
    assert app.animation.totalDuration == pytest.approx(6.0)

    app.animation.play()
    app.animation.advance(3.0)
    assert app.animation.progress == pytest.approx(0.5)


def test_export_refuses_operations_for_now() -> None:
    document, app = make_app()
    a, b = two_matrices(app)
    app.operations.compute("add", a, b, "")
    app.exporter._environment_state = "ready"
    assert not app.exporter.startExport()
    assert "2×2 transformations" in app.errorMessage


def test_operations_survive_save_and_open(tmp_path) -> None:
    document, app = make_app()
    a, b = two_matrices(app)
    app.operations.compute("multiply", a, b, "")
    app.project.saveProjectAs(str(tmp_path / "ops.mvscene"))
    app.project.newProject()
    assert app.operations.operationCount == 0

    app.project.openProject(str(tmp_path / "ops.mvscene"))
    assert app.operations.operationCount == 1 and app.operations.hasFocus
    assert app.operations.algebraView["title"] == "C = A · B"
    assert app.animation.segments == 4
