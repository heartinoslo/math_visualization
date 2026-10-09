"""Qt Quick 3D geometries filled from flat vertex data computed in Python.

The geometries are instantiated in QML, so the 3D scene owns them and Qt
destroys them in step with its render thread. View models only publish the
vertex data (mathematical coordinates) that QML binds to ``vertices``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from PySide6.QtCore import Property, Signal
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

from math_visualization.viewport.viewport_3d import SCENE_UNITS_PER_MATH_UNIT

Point3 = tuple[float, float, float]


def flatten(primitives: Iterable[Sequence[Point3]]) -> list[float]:
    """Flatten primitives (segments, triangles, …) into ``[x, y, z, x, y, z, …]``."""
    return [coordinate for primitive in primitives for point in primitive for coordinate in point]


def math_vertices_to_scene(vertices: Sequence[float]) -> np.ndarray:
    """Map flat mathematical ``(x, y, z)`` vertices to an ``(n, 3)`` float32 scene array.

    Mathematical ``(x, y, z)`` maps to scene ``(x, z, -y)`` scaled by
    ``SCENE_UNITS_PER_MATH_UNIT``, matching :func:`viewport_3d.math_to_scene`.
    """
    points = np.asarray(vertices, dtype=np.float64).reshape(-1, 3)
    scene = np.empty_like(points)
    scene[:, 0] = points[:, 0]
    scene[:, 1] = points[:, 2]
    scene[:, 2] = -points[:, 1]
    return (scene * SCENE_UNITS_PER_MATH_UNIT).astype(np.float32)


class _VertexGeometry(QQuick3DGeometry):
    verticesChanged = Signal()

    def __init__(self, primitive: QQuick3DGeometry.PrimitiveType, parent=None):
        super().__init__(parent)
        self._vertices: list[float] = []
        self.setPrimitiveType(primitive)
        self.setStride(3 * 4)
        self.addAttribute(
            QQuick3DGeometry.Attribute.Semantic.PositionSemantic,
            0,
            QQuick3DGeometry.Attribute.ComponentType.F32Type,
        )

    def _get_vertices(self) -> list[float]:
        return self._vertices

    def _set_vertices(self, vertices: list[float]) -> None:
        self._vertices = list(vertices)
        scene = math_vertices_to_scene(self._vertices)
        self.setVertexData(scene.tobytes())
        if len(scene):
            self.setBounds(QVector3D(*scene.min(axis=0)), QVector3D(*scene.max(axis=0)))
        self.update()
        self.verticesChanged.emit()

    @property
    def vertex_count(self) -> int:
        return len(self._vertices) // 3


class LineSetGeometry(_VertexGeometry):
    """Many line segments in one draw call: ``vertices`` holds two points per segment.

    Grids are drawn as a single model instead of one model per line, as the
    performance principles in the development plan require.
    """

    def __init__(self, parent=None):
        super().__init__(QQuick3DGeometry.PrimitiveType.Lines, parent)

    vertices = Property("QVariantList", _VertexGeometry._get_vertices, _VertexGeometry._set_vertices,
                        notify=_VertexGeometry.verticesChanged)


class TriangleGeometry(_VertexGeometry):
    """Filled triangles: ``vertices`` holds three points per triangle."""

    def __init__(self, parent=None):
        super().__init__(QQuick3DGeometry.PrimitiveType.Triangles, parent)

    vertices = Property("QVariantList", _VertexGeometry._get_vertices, _VertexGeometry._set_vertices,
                        notify=_VertexGeometry.verticesChanged)


def fan_triangles(points: Sequence[Point3]) -> list[tuple[Point3, Point3, Point3]]:
    """Triangulate a convex polygon given in order."""
    return [(points[0], points[index], points[index + 1]) for index in range(1, len(points) - 1)]
