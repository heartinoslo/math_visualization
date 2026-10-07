"""Tests for converting scene documents to and from plain data."""

import json

import pytest

from math_visualization.math_core import Vector2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.serialization import (
    SceneFormatError,
    document_from_dict,
    document_to_dict,
)
from math_visualization.scene.vector_object import VectorObject
from math_visualization.scene.workspace_state import CameraState2D, CameraState3D, WorkspaceMode


def populated_document() -> SceneDocument:
    document = SceneDocument(title="Experiment")
    document.workspace_mode = WorkspaceMode.THREE_D
    document.workspace_state_2d = CameraState2D(1.5, -2.0, 3.0)
    document.workspace_state_3d = CameraState3D(0.5, 0.0, 0.0, 120.0, 15.0, 8.0, "orthographic")
    document.vectors = [
        VectorObject("a1", "u", "#F59E0B", Vector2(2, 1)),
        VectorObject("b2", "v", "#A78BFA", Vector2(-0.5, 3.25)),
    ]
    document.selected_object_id = "b2"
    return document


def test_round_trip_through_json_preserves_everything() -> None:
    document = populated_document()

    restored = document_from_dict(json.loads(json.dumps(document_to_dict(document))))

    assert restored == document


def test_vectors_are_serialized_as_plain_components() -> None:
    data = document_to_dict(populated_document())

    assert data["mathematical_dimension"] == 2
    assert data["vectors"][0] == {"id": "a1", "name": "u", "color": "#F59E0B", "components": [2.0, 1.0]}


def mutate(change):
    data = document_to_dict(populated_document())
    change(data)
    return data


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(schema_version=2),
        lambda d: d.pop("vectors"),
        lambda d: d["vectors"][0].update(components=[1.0]),
        lambda d: d["vectors"][0].update(components=[1.0, "2"]),
        lambda d: d["vectors"][0].update(components=[1.0, float("nan")]),
        lambda d: d["vectors"][1].update(id="a1"),
        lambda d: d.update(selected_object_id="missing"),
        lambda d: d.update(workspace_mode="4d"),
        lambda d: d["workspace_state_2d"].update(zoom=0),
        lambda d: d["vectors"][0].update(color="orange"),
    ],
)
def test_invalid_data_is_rejected_with_a_format_error(change) -> None:
    with pytest.raises(SceneFormatError):
        document_from_dict(mutate(change))


def test_non_object_input_is_rejected() -> None:
    with pytest.raises(SceneFormatError):
        document_from_dict([1, 2, 3])
