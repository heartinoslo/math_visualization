"""Tests for the scene objects and inspector view models."""

import pytest
from PySide6.QtCore import Qt

from math_visualization.math_core import Vector2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import VECTOR_PALETTE
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel
from math_visualization.viewmodels.formatting import format_number, parse_number


def make_app():
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    return document, view_model, view_model.scene, view_model.inspector


def record(signal) -> list:
    emissions: list = []
    signal.connect(lambda *arguments: emissions.append(arguments))
    return emissions


def test_add_creates_named_coloured_vectors_at_one_one_and_selects_them() -> None:
    document, keep_alive, scene, _ = make_app()
    selections = record(scene.selectionChanged)

    ids = [scene.addVector() for _ in range(4)]

    assert [vector.name for vector in document.vectors] == ["u", "v", "w", "a"]
    assert [vector.color for vector in document.vectors] == list(VECTOR_PALETTE[:4])
    assert all(vector.vector == Vector2(1, 1) for vector in document.vectors)
    assert scene.selectedId == ids[-1]
    assert len(selections) == 4
    assert scene.vectorCount == 4


def test_list_model_exposes_rows_and_selection() -> None:
    _, keep_alive, scene, _ = make_app()
    first = scene.addVector()
    scene.addVector()
    model = scene.vectorModel
    roles = {bytes(name).decode(): role for role, name in model.roleNames().items()}

    assert model.rowCount() == 2
    assert model.data(model.index(0), roles["name"]) == "u"
    assert model.data(model.index(0), roles["componentsText"]) == "(1, 1)"
    assert model.data(model.index(1), roles["selected"]) is True
    scene.select(first)
    assert model.data(model.index(0), roles["selected"]) is True
    assert model.data(model.index(0), Qt.DisplayRole) == "u"


def test_duplicate_inserts_after_source_with_a_new_name() -> None:
    document, keep_alive, scene, _ = make_app()
    first = scene.addVector()
    scene.addVector()
    scene.setComponents(first, 2.0, -1.0)
    scene.select(first)

    copy = scene.duplicateSelected()

    assert [vector.name for vector in document.vectors] == ["u", "w", "v"]
    assert document.find_vector(copy).vector == Vector2(2, -1)
    assert scene.selectedId == copy


def test_remove_selected_and_undo() -> None:
    document, keep_alive, scene, _ = make_app()
    first = scene.addVector()
    scene.addVector()
    scene.select(first)

    scene.removeSelected()
    assert [vector.name for vector in document.vectors] == ["v"]
    assert scene.selectedId == ""

    assert scene.undo()
    assert [vector.name for vector in document.vectors] == ["u", "v"]
    assert scene.selectedId == first


def test_rename_rejects_duplicates_and_empty_names() -> None:
    document, view_model, scene, _ = make_app()
    first = scene.addVector()
    scene.addVector()

    assert scene.rename(first, "p")
    assert not scene.rename(first, "v")
    assert "already used" in view_model.errorMessage
    assert not scene.rename(first, "   ")
    assert document.find_vector(first).name == "p"


def test_drag_is_one_undo_step_and_selects() -> None:
    document, keep_alive, scene, _ = make_app()
    first = scene.addVector()
    scene.addVector()
    history = scene.commands.undo_count

    assert scene.beginDrag(first)
    for step in range(10):
        scene.dragTo(1.0 + step * 0.1, 1.0)
    scene.endDrag()

    assert scene.selectedId == first
    assert document.find_vector(first).vector == Vector2(1.9, 1.0)
    assert scene.commands.undo_count == history + 1
    scene.undo()
    assert document.find_vector(first).vector == Vector2(1, 1)


def test_inspector_shows_and_edits_the_selection() -> None:
    document, view_model, scene, inspector = make_app()
    assert inspector.hasSelection is False
    identifier = scene.addVector()

    assert inspector.setXText("2")
    assert inspector.setYText(" −1.5 ")
    assert (inspector.xText, inspector.yText) == ("2", "-1.5")
    assert inspector.lengthText == format_number(Vector2(2, -1.5).length)
    assert inspector.angleText == "-36.87°"
    assert inspector.setName("p") and inspector.name == "p"
    assert inspector.setColor(VECTOR_PALETTE[3]) and inspector.color == VECTOR_PALETTE[3]
    assert document.find_vector(identifier).vector == Vector2(2, -1.5)


def test_inspector_rejects_bad_numbers_without_changing_the_vector() -> None:
    document, view_model, scene, inspector = make_app()
    scene.addVector()

    assert not inspector.setXText("abc")
    assert "not a number" in view_model.errorMessage
    assert not inspector.setYText("inf")
    assert document.vectors[0].vector == Vector2(1, 1)


def test_inspector_reports_the_zero_vector() -> None:
    _, keep_alive, scene, inspector = make_app()
    scene.addVector()
    inspector.setXText("0")
    inspector.setYText("0")

    assert inspector.isZero
    assert inspector.angleText == "undefined (zero vector)"


@pytest.mark.parametrize(
    ("value", "text"), [(2.0, "2"), (-1.5, "-1.5"), (1 / 3, "0.3333"), (-0.00001, "0"), (1e6, "1000000")]
)
def test_format_number(value, text) -> None:
    assert format_number(value) == text


def test_parse_number() -> None:
    assert parse_number(" 2,5 ") == 2.5
    assert parse_number("−3") == -3.0
    for text in ("", "nan", "1e400", "two"):
        with pytest.raises(ValueError):
            parse_number(text)
