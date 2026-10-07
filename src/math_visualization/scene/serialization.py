"""Convert a :class:`SceneDocument` to and from plain JSON-compatible data.

Only data conversion lives here; reading and writing project files is the
persistence layer's job (Stage 7). ``document_from_dict`` validates
everything it reads and raises :class:`SceneFormatError` on bad input, so a
corrupt file can never produce a half-built document.
"""

from __future__ import annotations

from typing import Any

from math_visualization.math_core.vector2 import Vector2
from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import VectorObject
from math_visualization.scene.workspace_state import (
    CameraState2D,
    CameraState3D,
    WorkspaceMode,
)


CURRENT_SCHEMA_VERSION = 1


class SceneFormatError(ValueError):
    """Raised when serialized scene data is malformed or unsupported."""


def document_to_dict(document: SceneDocument) -> dict[str, Any]:
    camera_2d = document.workspace_state_2d
    camera_3d = document.workspace_state_3d
    return {
        "schema_version": document.schema_version,
        "document_id": document.document_id,
        "title": document.title,
        "mathematical_dimension": 2,
        "workspace_mode": document.workspace_mode.value,
        "workspace_state_2d": {
            "center_x": camera_2d.center_x,
            "center_y": camera_2d.center_y,
            "zoom": camera_2d.zoom,
        },
        "workspace_state_3d": {
            "target": [camera_3d.target_x, camera_3d.target_y, camera_3d.target_z],
            "azimuth": camera_3d.azimuth,
            "elevation": camera_3d.elevation,
            "distance": camera_3d.distance,
            "projection_mode": camera_3d.projection_mode.value,
        },
        "animation": {
            "progress": document.animation_state.progress,
            "duration": document.animation_state.duration,
        },
        "vectors": [
            {
                "id": vector.object_id,
                "name": vector.name,
                "color": vector.color,
                "components": [vector.vector.x, vector.vector.y],
            }
            for vector in document.vectors
        ],
        "selected_object_id": document.selected_object_id,
    }


def document_from_dict(data: Any) -> SceneDocument:
    """Build a document from ``data`` or raise :class:`SceneFormatError`."""
    try:
        return _document_from_dict(data)
    except SceneFormatError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SceneFormatError(f"Invalid scene data: {error}") from error


def _document_from_dict(data: Any) -> SceneDocument:
    _require(isinstance(data, dict), "scene data must be an object")
    version = data["schema_version"]
    _require(
        isinstance(version, int) and not isinstance(version, bool),
        "schema_version must be an integer",
    )
    if version != CURRENT_SCHEMA_VERSION:
        raise SceneFormatError(
            f"Unsupported schema version {version}; this build reads version {CURRENT_SCHEMA_VERSION}"
        )

    camera_2d = data["workspace_state_2d"]
    camera_3d = data["workspace_state_3d"]
    target = camera_3d["target"]
    _require(isinstance(target, list) and len(target) == 3, "3D target must have three numbers")
    animation = data["animation"]

    vectors: list[VectorObject] = []
    for entry in data["vectors"]:
        components = entry["components"]
        _require(
            isinstance(components, list) and len(components) == 2,
            "vector components must have two numbers",
        )
        vectors.append(
            VectorObject(
                object_id=_string(entry["id"], "vector id"),
                name=_string(entry["name"], "vector name"),
                color=_string(entry["color"], "vector color"),
                vector=Vector2(_number(components[0]), _number(components[1])),
            )
        )
    ids = [vector.object_id for vector in vectors]
    _require(len(set(ids)) == len(ids), "vector ids must be unique")

    selected = data.get("selected_object_id")
    _require(selected is None or selected in ids, "selected_object_id must name a vector")

    return SceneDocument(
        title=_string(data["title"], "title"),
        schema_version=version,
        document_id=_string(data["document_id"], "document_id"),
        workspace_mode=WorkspaceMode(data["workspace_mode"]),
        workspace_state_2d=CameraState2D(
            center_x=_number(camera_2d["center_x"]),
            center_y=_number(camera_2d["center_y"]),
            zoom=_number(camera_2d["zoom"]),
        ),
        workspace_state_3d=CameraState3D(
            target_x=_number(target[0]),
            target_y=_number(target[1]),
            target_z=_number(target[2]),
            azimuth=_number(camera_3d["azimuth"]),
            elevation=_number(camera_3d["elevation"]),
            distance=_number(camera_3d["distance"]),
            projection_mode=camera_3d["projection_mode"],
        ),
        animation_state=AnimationState(
            progress=_number(animation["progress"]),
            duration=_number(animation["duration"]),
        ),
        vectors=vectors,
        selected_object_id=selected,
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SceneFormatError(message)


def _number(value: Any) -> float:
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"expected a number, got {value!r}",
    )
    return float(value)


def _string(value: Any, name: str) -> str:
    _require(isinstance(value, str), f"{name} must be a string")
    return value
