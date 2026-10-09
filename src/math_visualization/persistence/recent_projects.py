"""The most recently opened or saved project files."""

from __future__ import annotations

import os
from typing import Protocol


MAX_RECENT_PROJECTS = 8


class RecentStorage(Protocol):
    def read(self) -> list[str]: ...
    def write(self, paths: list[str]) -> None: ...


class MemoryStorage:
    """Keeps the list for this process only (tests and the default)."""

    def __init__(self, paths: list[str] | None = None):
        self._paths = list(paths or [])

    def read(self) -> list[str]:
        return list(self._paths)

    def write(self, paths: list[str]) -> None:
        self._paths = list(paths)


class SettingsStorage:
    """Persists the list in a ``QSettings`` (the user's application settings)."""

    KEY = "recentProjects"

    def __init__(self, settings):
        self._settings = settings

    def read(self) -> list[str]:
        value = self._settings.value(self.KEY, [])
        if isinstance(value, str):
            # QSettings collapses a one-element list into a plain string.
            value = [value]
        return [path for path in value or [] if isinstance(path, str)]

    def write(self, paths: list[str]) -> None:
        self._settings.setValue(self.KEY, list(paths))
        self._settings.sync()


def _key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


class RecentProjects:
    def __init__(self, storage: RecentStorage | None = None):
        self._storage = storage or MemoryStorage()

    def paths(self) -> list[str]:
        return self._storage.read()

    def add(self, path: str) -> None:
        """Move ``path`` to the front, keeping at most :data:`MAX_RECENT_PROJECTS`."""
        path = os.path.abspath(path)
        others = [item for item in self.paths() if _key(item) != _key(path)]
        self._storage.write([path, *others][:MAX_RECENT_PROJECTS])

    def remove(self, path: str) -> None:
        self._storage.write([item for item in self.paths() if _key(item) != _key(path)])

    def clear(self) -> None:
        self._storage.write([])
