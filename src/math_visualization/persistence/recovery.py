"""Crash recovery: a snapshot of unsaved work, written periodically while the project is dirty.

The snapshot is an ordinary project file with an extra ``recovery`` entry that
remembers which file (if any) the work belonged to. It is deleted whenever the
work is saved or deliberately discarded, so finding one at startup means the
previous session ended without saving.
"""

from __future__ import annotations

import datetime as _datetime
from dataclasses import dataclass
from pathlib import Path

from math_visualization.persistence.project_file import (
    ProjectFileError,
    read_project_data,
    upgrade,
    write_project,
)
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.serialization import SceneFormatError, document_from_dict


RECOVERY_FILE_NAME = "recovery.mvscene"


@dataclass(frozen=True)
class RecoveredWork:
    document: SceneDocument
    original_path: str | None
    saved_at: str


class RecoveryStore:
    def __init__(self, directory: str | Path):
        self.path = Path(directory) / RECOVERY_FILE_NAME

    def exists(self) -> bool:
        return self.path.is_file()

    def write(self, document: SceneDocument, original_path: str | None) -> None:
        saved_at = _datetime.datetime.now().isoformat(timespec="seconds")
        write_project(document, self.path, recovery={"original_path": original_path, "saved_at": saved_at})

    def read(self) -> RecoveredWork:
        """Load the snapshot or raise :class:`ProjectFileError`."""
        data = read_project_data(self.path)
        meta = data.get("recovery")
        if not isinstance(meta, dict):
            raise ProjectFileError("The recovery snapshot is damaged")
        original = meta.get("original_path")
        try:
            document = document_from_dict(upgrade(data, "The recovery snapshot"))
        except SceneFormatError as error:
            raise ProjectFileError(f"The recovery snapshot is damaged: {error}") from error
        return RecoveredWork(
            document=document,
            original_path=original if isinstance(original, str) and original else None,
            saved_at=str(meta.get("saved_at", "")),
        )

    def discard(self) -> None:
        self.path.unlink(missing_ok=True)
