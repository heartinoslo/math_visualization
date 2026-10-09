"""Small key/value preferences (export settings and the like)."""

from __future__ import annotations

from typing import Protocol


class SettingsStore(Protocol):
    def get(self, key: str, default: str = "") -> str: ...
    def set(self, key: str, value: str) -> None: ...


class MemorySettings:
    """Preferences for this process only (tests and the default)."""

    def __init__(self, values: dict[str, str] | None = None):
        self._values = dict(values or {})

    def get(self, key: str, default: str = "") -> str:
        return self._values.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._values[key] = value


class QtSettings:
    """Preferences stored in a ``QSettings`` (the user's application settings)."""

    def __init__(self, settings):
        self._settings = settings

    def get(self, key: str, default: str = "") -> str:
        value = self._settings.value(key, default)
        return value if isinstance(value, str) else default

    def set(self, key: str, value: str) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()
