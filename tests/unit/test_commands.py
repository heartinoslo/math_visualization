"""Tests for undoable vector commands and the command manager."""

import pytest

from math_visualization.commands import (
    AddVectorCommand,
    CommandManager,
    RemoveVectorCommand,
    UpdateVectorCommand,
)
from math_visualization.math_core import Vector2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import VectorObject


def vector(object_id="a", name="u", x=1.0, y=1.0) -> VectorObject:
    return VectorObject(object_id, name, "#F59E0B", Vector2(x, y))


def make_manager():
    document = SceneDocument()
    changes = []
    return document, CommandManager(document, changes.append), changes


def test_add_selects_and_undo_restores_previous_selection() -> None:
    document, manager, changes = make_manager()
    manager.execute(AddVectorCommand(vector("a")))
    manager.execute(AddVectorCommand(vector("b", "v")))

    assert [v.object_id for v in document.vectors] == ["a", "b"]
    assert document.selected_object_id == "b"
    manager.undo()
    assert [v.object_id for v in document.vectors] == ["a"]
    assert document.selected_object_id == "a"
    manager.redo()
    assert document.selected_object_id == "b"
    assert len(changes) == 4


def test_adding_a_duplicate_id_fails_without_changing_anything() -> None:
    document, manager, _ = make_manager()
    manager.execute(AddVectorCommand(vector("a")))

    with pytest.raises(ValueError):
        manager.execute(AddVectorCommand(vector("a", "v")))
    assert len(document.vectors) == 1 and manager.undo_count == 1


def test_remove_clears_selection_and_undo_reinserts_in_place() -> None:
    document, manager, _ = make_manager()
    for object_id, name in (("a", "u"), ("b", "v"), ("c", "w")):
        manager.execute(AddVectorCommand(vector(object_id, name)))
    document.selected_object_id = "b"

    manager.execute(RemoveVectorCommand("b"))
    assert [v.object_id for v in document.vectors] == ["a", "c"]
    assert document.selected_object_id is None

    manager.undo()
    assert [v.object_id for v in document.vectors] == ["a", "b", "c"]
    assert document.selected_object_id == "b"


def test_update_and_undo() -> None:
    document, manager, _ = make_manager()
    manager.execute(AddVectorCommand(vector("a")))

    manager.execute(UpdateVectorCommand(vector("a"), vector("a", x=2.0)))
    assert document.vectors[0].vector == Vector2(2, 1)
    manager.undo()
    assert document.vectors[0].vector == Vector2(1, 1)


def test_drag_updates_merge_into_one_undo_step() -> None:
    document, manager, _ = make_manager()
    manager.execute(AddVectorCommand(vector("a")))
    previous = document.vectors[0]
    for step in range(1, 6):
        current = vector("a", x=1.0 + step)
        manager.execute(UpdateVectorCommand(previous, current, merge_key="drag-1"))
        previous = current
    manager.execute(UpdateVectorCommand(previous, vector("a", x=9.0), merge_key="drag-2"))

    assert manager.undo_count == 3
    manager.undo()
    assert document.vectors[0].vector == Vector2(6, 1)
    manager.undo()
    assert document.vectors[0].vector == Vector2(1, 1)


def test_new_edit_clears_redo_history() -> None:
    document, manager, _ = make_manager()
    manager.execute(AddVectorCommand(vector("a")))
    manager.undo()
    assert manager.can_redo

    manager.execute(AddVectorCommand(vector("b", "v")))

    assert not manager.can_redo
    assert manager.redo() is False
    assert [v.object_id for v in document.vectors] == ["b"]


def test_undo_on_empty_history_is_a_no_op() -> None:
    _, manager, changes = make_manager()

    assert manager.undo() is False
    assert changes == []
