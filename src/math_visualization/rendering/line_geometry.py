"""A Qt Quick 3D geometry that draws a batch of line segments in one draw call."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

from math_visualization.viewport.viewport_3d import SCENE_UNITS_PER_MATH_UNIT

Segment = tuple[tuple[float, float, float], tuple[float, float, float]]


def segments_to_scene_vertices(segments: Sequence[Segment]) -> np.ndarray:
    """Return an ``(n * 2, 3)`` float32 array of scene-space vertices.

    Mathematical ``(x, y, z)`` maps to scene ``(x, z, -y)`` scaled by
    ``SCENE_UNITS_PER_MATH_UNIT``, matching :func:`viewport_3d.math_to_scene`.
    """
    if not segments:
        return np.zeros((0, 3), dtype=np.float32)
    points = np.asarray(segments, dtype=np.float64).reshape(-1, 3)
    scene = np.empty_like(points)
    scene[:, 0] = points[:, 0]
    scene[:, 1] = points[:, 2]
    scene[:, 2] = -points[:, 1]
    return (scene * SCENE_UNITS_PER_MATH_UNIT).astype(np.float32)


class LineSetGeometry(QQuick3DGeometry):
    """Many line segments uploaded as one vertex buffer.

    Grids are drawn as a single model instead of one model per line, as the
    performance principles in the development plan require.
    """

    def __init__(self):
        super().__init__()
        self._vertex_count = 0
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Lines)
        self.setStride(3 * 4)
        self.addAttribute(
            QQuick3DGeometry.Attribute.Semantic.PositionSemantic,
            0,
            QQuick3DGeometry.Attribute.ComponentType.F32Type,
        )

    @property
    def vertex_count(self) -> int:
        return self._vertex_count

    def set_segments(self, segments: Sequence[Segment]) -> None:
        vertices = segments_to_scene_vertices(segments)
        self._vertex_count = len(vertices)
        self.setVertexData(vertices.tobytes())
        if len(vertices):
            self.setBounds(QVector3D(*vertices.min(axis=0)), QVector3D(*vertices.max(axis=0)))
        self.update()
