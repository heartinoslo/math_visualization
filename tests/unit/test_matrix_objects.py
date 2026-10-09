"""Tests for named matrices: naming, the active matrix and their undoable commands."""

import pytest

from math_visualization.commands import (
    AddMatrixCommand,
    CommandManager,
    RemoveMatrixCommand,
    UpdateMatrixCommand,
)
from math_visualization.math_core import Matrix2
from math_visualization.scene.matrix_object import MatrixObject, next_matrix_name
from math_visualization.scene.scene_document import SceneDocument


def named(name: str, matrix: Matrix2 = Matrix2.identity()) -> MatrixObject:
    return MatrixObject(f"id-{name}", name, matrix)


def test_names_skip_i_and_continue_with_subscripts() -> None:
    assert next_matrix_name([]) == "A"
    assert next_matrix_name(["A", "B", "C", "D", "E", "F", "G", "H"]) == "J"
    every_letter = list("ABCDEFGHJKLMNPQRSTUVWXYZ")
    assert next_matrix_name(every_letter) == "A₁"
    assert "I" not in every_letter and "O" not in every_letter


def test_matrix_object_validates_its_name() -> None:
    assert MatrixObject("x", "  B ", Matrix2.identity()).name == "B"
    with pytest.raises(ValueError):
        MatrixObject("x", " ", Matrix2.identity())
    with pytest.raises(ValueError):
        MatrixObject("x", "M" * 25, Matrix2.identity())


def test_new_document_has_an_active_identity_a() -> None:
    document = SceneDocument()
    assert [matrix.name for matrix in document.matrices] == ["A"]
    assert document.active_matrix.name == "A" and document.matrix == Matrix2.identity()


def test_matrix_property_edits_the_active_matrix() -> None:
    document = SceneDocument(matrices=[named("A"), named("B")], active_matrix_id="id-B")
    document.matrix = Matrix2(2, 0, 0, 2)
    assert document.find_matrix("id-B").matrix == Matrix2(2, 0, 0, 2)
    assert document.find_matrix("id-A").matrix == Matrix2.identity()

    empty = SceneDocument(matrices=[])
    empty.matrix = Matrix2(0, -1, 1, 0)
    assert empty.active_matrix.name == "A" and empty.matrix == Matrix2(0, -1, 1, 0)


def test_add_activates_and_undo_restores_the_previous_active() -> None:
    document = SceneDocument(matrices=[named("A")])
    commands = CommandManager(document)

    commands.execute(AddMatrixCommand(named("B")))
    assert document.active_matrix_id == "id-B"
    assert commands.undo_label == "Add B"
    commands.undo()
    assert [m.name for m in document.matrices] == ["A"] and document.active_matrix_id == "id-A"


def test_removing_the_active_matrix_activates_a_neighbour() -> None:
    document = SceneDocument(matrices=[named("A"), named("B"), named("C")], active_matrix_id="id-C")
    commands = CommandManager(document)

    commands.execute(RemoveMatrixCommand("id-C"))
    assert document.active_matrix_id == "id-B"
    commands.execute(RemoveMatrixCommand("id-A"))
    assert document.active_matrix_id == "id-B"
    commands.execute(RemoveMatrixCommand("id-B"))
    assert document.matrices == [] and document.active_matrix_id is None
    assert document.matrix == Matrix2.identity()

    commands.undo()
    commands.undo()
    commands.undo()
    assert [m.name for m in document.matrices] == ["A", "B", "C"]
    assert document.active_matrix_id == "id-C"


def test_update_activates_its_matrix_on_execute_and_undo() -> None:
    document = SceneDocument(matrices=[named("A"), named("B")], active_matrix_id="id-A")
    commands = CommandManager(document)
    edited = named("B", Matrix2(1, 1, 0, 1))

    commands.execute(UpdateMatrixCommand(named("B"), edited))
    assert document.active_matrix_id == "id-B" and commands.undo_label == "Edit B"
    document.active_matrix_id = "id-A"
    commands.undo()
    assert document.active_matrix_id == "id-B"
    assert document.find_matrix("id-B").matrix == Matrix2.identity()

    commands.execute(UpdateMatrixCommand(named("B"), MatrixObject("id-B", "R", Matrix2.identity())))
    assert commands.undo_label == "Rename B"


def test_update_must_keep_the_identity() -> None:
    with pytest.raises(ValueError):
        UpdateMatrixCommand(named("A"), named("B"))
