"""Reading and writing project files (``.mvscene``, JSON).

A project file is the serialized :class:`SceneDocument` plus a ``format``
marker, so any other JSON file is rejected with a clear message. Writing goes
through a temporary file that replaces the target only once it is complete,
so a crash or a full disk never leaves a half-written project behind.

Every failure is reported as :class:`ProjectFileError` with a message meant
for the user; nothing in here lets a bad file crash the application.

Schema policy
-------------
* A file from a *newer* schema than this build understands is refused (the
  user is told to update the application); it is never guessed at.
* A file from an *older* schema is upgraded step by step through
  :data:`MIGRATIONS` before validation.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from math_visualization import __version__
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.serialization import (
    CURRENT_SCHEMA_VERSION,
    SceneFormatError,
    document_from_dict,
    document_to_dict,
)


FILE_EXTENSION = ".mvscene"
FILE_FORMAT = "math-visualization-scene"
# Scenes are a few kilobytes; anything far larger is not one of ours.
MAX_FILE_BYTES = 16 * 1024 * 1024

# MIGRATIONS[n] upgrades the data of schema version n to version n + 1.
Migration = Callable[[dict[str, Any]], dict[str, Any]]


def _single_matrix_to_named_matrices(data: dict[str, Any]) -> dict[str, Any]:
    """1 → 2: the one ``matrix`` becomes the named matrix "A", which is active."""
    if "matrix" not in data:
        raise SceneFormatError("matrix is missing")
    identifier = uuid4().hex
    data["matrices"] = [{"id": identifier, "name": "A", "size": 2, "entries": data.pop("matrix")}]
    data["active_matrix_id"] = identifier
    return data


MIGRATIONS: dict[int, Migration] = {1: _single_matrix_to_named_matrices}


class ProjectFileError(Exception):
    """A project could not be read or written; ``str(error)`` is shown to the user."""


def project_to_data(document: SceneDocument, **extra: Any) -> dict[str, Any]:
    data = {"format": FILE_FORMAT, "app_version": __version__}
    data.update(document_to_dict(document))
    data.update(extra)
    return data


def write_project(document: SceneDocument, path: str | os.PathLike, **extra: Any) -> None:
    """Write ``document`` to ``path`` atomically. ``extra`` adds top-level keys."""
    target = Path(path)
    text = json.dumps(project_to_data(document, **extra), indent=2, ensure_ascii=False, allow_nan=False)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    except OSError as error:
        raise ProjectFileError(f"Could not save {target.name}: {error.strerror or error}") from error


def read_project_data(path: str | os.PathLike) -> dict[str, Any]:
    """Read and decode the JSON object of a project file, without building the document."""
    source = Path(path)
    try:
        size = source.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ProjectFileError(f"{source.name} is too large to be a scene file ({size // 1024} KB)")
        raw = source.read_bytes()
    except FileNotFoundError as error:
        raise ProjectFileError(f"{source.name} no longer exists") from error
    except OSError as error:
        raise ProjectFileError(f"Could not open {source.name}: {error.strerror or error}") from error
    try:
        data = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
    except UnicodeDecodeError as error:
        raise ProjectFileError(f"{source.name} is not a scene file (it is not UTF-8 text)") from error
    except json.JSONDecodeError as error:
        raise ProjectFileError(
            f"{source.name} is damaged: invalid JSON at line {error.lineno}, column {error.colno}"
        ) from error
    except ValueError as error:
        raise ProjectFileError(f"{source.name} is damaged: {error}") from error
    if not isinstance(data, dict) or data.get("format") != FILE_FORMAT:
        raise ProjectFileError(f"{source.name} is not a Math Visualization scene file")
    return data


def read_project(path: str | os.PathLike) -> SceneDocument:
    """Load a project file, upgrading older schemas, or raise :class:`ProjectFileError`."""
    name = Path(path).name
    data = read_project_data(path)
    try:
        return document_from_dict(upgrade(data, name))
    except SceneFormatError as error:
        raise ProjectFileError(f"{name} is damaged: {error}") from error


def upgrade(data: dict[str, Any], name: str = "The file") -> dict[str, Any]:
    """Apply :data:`MIGRATIONS` until ``data`` has the current schema version."""
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ProjectFileError(f"{name} is damaged: missing or invalid schema_version")
    if version > CURRENT_SCHEMA_VERSION:
        raise ProjectFileError(
            f"{name} was saved by a newer version of Math Visualization (scene format {version}); "
            f"this version reads format {CURRENT_SCHEMA_VERSION} and older. Please update the application."
        )
    while version < CURRENT_SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ProjectFileError(f"{name} uses scene format {version}, which can no longer be opened")
        data = migration(dict(data))
        version += 1
        data["schema_version"] = version
    return data


def _reject_constant(name: str) -> None:
    raise ValueError(f"{name} is not a valid number")
