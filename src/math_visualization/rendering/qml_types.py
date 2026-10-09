"""Registration of the Python rendering types used from QML."""

from __future__ import annotations

from PySide6.QtQml import qmlRegisterType

from math_visualization.rendering.line_geometry import LineSetGeometry, TriangleGeometry

QML_MODULE = "MathVisualization.Rendering"
_registered = False


def register_qml_types() -> None:
    """Make ``LineSetGeometry`` and ``TriangleGeometry`` available to QML (once per process)."""
    global _registered
    if _registered:
        return
    _registered = True
    qmlRegisterType(LineSetGeometry, QML_MODULE, 1, 0, "LineSetGeometry")
    qmlRegisterType(TriangleGeometry, QML_MODULE, 1, 0, "TriangleGeometry")
