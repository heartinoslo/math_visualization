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


# 3×3 matrices and recorded operations -------------------------------------------------------

from math_visualization.commands import AddOperationCommand, RemoveOperationCommand  # noqa: E402
from math_visualization.math_core.matrix3 import Matrix3  # noqa: E402
from math_visualization.math_core.matrix_algebra import OperationKind  # noqa: E402
from math_visualization.scene.operation_record import OperationRecord  # noqa: E402
from math_visualization.scene.serialization import (  # noqa: E402
    SceneFormatError,
    document_from_dict,
    document_to_dict,
)

M3 = Matrix3((1, 2, 3, 0, 1, 4, 5, 6, 0))


def product_record() -> tuple[OperationRecord, MatrixObject]:
    operands = (Matrix2(1, 2, 3, 4), Matrix2(0, 1, -1, 2))
    record = OperationRecord("op1", OperationKind.MULTIPLY, ("A", "B"), operands, None, "C", "id-C")
    return record, MatrixObject("id-C", "C", operands[0] @ operands[1])


def test_3x3_objects_do_not_drive_the_plane_transformation() -> None:
    document = SceneDocument(matrices=[MatrixObject("m", "M", M3)])
    assert document.active_matrix.size == 3
    assert document.matrix == Matrix2.identity()


def test_add_operation_records_and_activates_its_result_in_one_step() -> None:
    document = SceneDocument(matrices=[named("A")], active_matrix_id="id-A")
    commands = CommandManager(document)
    record, result = product_record()

    commands.execute(AddOperationCommand(record, result))
    assert document.active_operation_id == "op1" and document.active_matrix_id == "id-C"
    assert commands.undo_label == "Compute C = A · B"

    commands.undo()
    assert document.operations == [] and [m.name for m in document.matrices] == ["A"]
    assert document.active_operation_id is None and document.active_matrix_id == "id-A"


def test_editing_a_matrix_moves_the_focus_off_the_operation() -> None:
    document = SceneDocument(matrices=[named("A")], active_matrix_id="id-A")
    commands = CommandManager(document)
    record, result = product_record()
    commands.execute(AddOperationCommand(record, result))

    commands.execute(UpdateMatrixCommand(result, MatrixObject("id-C", "C", Matrix2.identity())))
    assert document.active_operation_id is None

    commands.execute(RemoveOperationCommand("op1"))
    assert document.operations == [] and document.find_matrix("id-C") is not None
    commands.undo()
    assert document.operations == [record]


def test_3x3_matrices_and_operations_round_trip() -> None:
    record, result = product_record()
    det = OperationRecord("op2", OperationKind.DETERMINANT, ("M",), (M3,))
    document = SceneDocument(
        matrices=[MatrixObject("m", "M", M3), result],
        operations=[record, det],
        active_operation_id="op2",
    )

    data = document_to_dict(document)
    assert data["matrices"][0]["size"] == 3 and len(data["matrices"][0]["entries"]) == 3
    assert data["operations"][1] == {
        "id": "op2", "kind": "determinant",
        "operands": [{"name": "M", "size": 3, "entries": [[1.0, 2.0, 3.0], [0.0, 1.0, 4.0], [5.0, 6.0, 0.0]]}],
        "scalar": None, "result_name": "", "result_matrix_id": None,
    }
    restored = document_from_dict(data)
    assert restored == document
    assert restored.active_operation.title == "det M = 1"


def test_inconsistent_operations_are_rejected() -> None:
    record, result = product_record()
    data = document_to_dict(SceneDocument(matrices=[result], operations=[record]))
    data["operations"][0]["operands"][1] = {"name": "B", "size": 3, "entries": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
    try:
        document_from_dict(data)
    except SceneFormatError as error:
        assert "same size" in str(error)
    else:
        raise AssertionError("mixed sizes were accepted")


def test_files_without_operations_still_open() -> None:
    data = document_to_dict(SceneDocument())
    data.pop("operations")
    data.pop("active_operation_id")
    assert document_from_dict(data).operations == []
