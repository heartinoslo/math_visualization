"""Tests for the matrices view model and how the active matrix drives editing and playback."""

from math_visualization.math_core import Matrix2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def make_app():
    document = SceneDocument()
    app = ApplicationViewModel(document)
    app.viewport2D.setViewportSize(800.0, 600.0)
    app.viewport3D.setViewportSize(900.0, 600.0)
    return document, app


def names(app) -> list[str]:
    model = app.matrices.matrixModel
    return [model.data(model.index(row), model.NameRole) for row in range(model.rowCount())]


def test_add_activates_the_new_matrix_and_editing_targets_it() -> None:
    document, app = make_app()
    first = document.active_matrix_id

    second = app.matrices.addMatrix()
    assert names(app) == ["A", "B"] and app.matrices.activeId == second
    assert app.transformation.matrixName == "B"

    app.transformation.applyPreset("shear")
    assert document.find_matrix(second).matrix == Matrix2(1, 1, 0, 1)
    assert document.find_matrix(first).matrix == Matrix2.identity()
    assert app.transformation.targetText == "B = [ 1  1 ; 0  1 ]"
    assert app.matrixProperties.determinantFormula.startswith("det B = ")

    app.matrices.activate(first)
    assert app.transformation.entryTexts == ["1", "0", "0", "1"]
    assert app.transformation.matrixName == "A"


def test_playback_follows_the_active_matrix() -> None:
    document, app = make_app()
    app.transformation.applyPreset("scale")
    app.matrices.addMatrix()
    app.transformation.applyPreset("rotation")
    app.animation.setProgress(1.0)

    assert app.transformation.current_matrix() == Matrix2(0, -1, 1, 0)
    app.matrices.activate(document.matrices[0].object_id)
    assert app.transformation.current_matrix() == Matrix2(2, 0, 0, 0.5)


def test_undo_brings_back_the_matrix_it_changes() -> None:
    document, app = make_app()
    a = document.active_matrix_id
    b = app.matrices.addMatrix()
    app.transformation.applyPreset("reflection")
    app.matrices.activate(a)

    app.project.undo()
    assert app.matrices.activeId == b
    assert document.find_matrix(b).matrix == Matrix2.identity()
    app.project.undo()
    assert names(app) == ["A"] and app.matrices.activeId == a


def test_duplicate_rename_and_remove() -> None:
    document, app = make_app()
    app.transformation.applyPreset("shear")
    copy = app.matrices.duplicateActive()
    assert names(app) == ["A", "B"]
    assert document.find_matrix(copy).matrix == Matrix2(1, 1, 0, 1)

    assert not app.matrices.rename(copy, "A")
    assert "already used" in app.errorMessage
    assert app.matrices.rename(copy, "Shear")
    assert names(app) == ["A", "Shear"] and app.project.undoText == "Undo Rename B"

    app.matrices.removeActive()
    assert names(app) == ["A"] and app.transformation.matrixName == "A"


def test_without_matrices_the_transformation_is_the_identity() -> None:
    _, app = make_app()
    app.transformation.applyPreset("shear")
    app.animation.setProgress(1.0)
    app.matrices.removeActive()

    assert not app.transformation.hasMatrix
    assert app.transformation.current_matrix() == Matrix2.identity()
    assert app.transformation.setEntryText(0, "3") is False
    assert "add one first" in app.errorMessage
    assert app.matrices.duplicateActive() == ""


def test_activating_is_not_an_unsaved_change(tmp_path) -> None:
    document, app = make_app()
    b = app.matrices.addMatrix()
    app.project.saveProjectAs(str(tmp_path / "two.mvscene"))
    assert not app.project.dirty

    app.matrices.activate(document.matrices[0].object_id)
    assert not app.project.dirty
    app.matrices.activate(b)
    app.transformation.applyPreset("shear")
    assert app.project.dirty


def test_opening_a_project_rebuilds_the_list(tmp_path) -> None:
    document, app = make_app()
    app.matrices.addMatrix()
    app.matrices.addMatrix()
    path = tmp_path / "three.mvscene"
    app.project.saveProjectAs(str(path))
    app.project.newProject()
    assert names(app) == ["A"]

    app.project.openProject(str(path))
    assert names(app) == ["A", "B", "C"]
    assert app.transformation.matrixName == "C"
