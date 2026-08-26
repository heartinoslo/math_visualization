"""Minimal exporter boundary reserved for a future Manim implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from math_visualization.scene.scene_document import SceneDocument


class SceneExporter(ABC):
    """Export a scene document without depending on QML or renderer objects."""

    @abstractmethod
    def export(self, document: SceneDocument) -> None:
        """Export ``document`` using a future concrete exporter."""
