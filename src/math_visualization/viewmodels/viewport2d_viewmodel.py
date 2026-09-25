"""2D viewport view model: grid layout, pan, zoom and cursor readout for QML."""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.workspace_viewmodel import WorkspaceViewModel
from math_visualization.viewport.viewport_2d import (
    GridLayout,
    Viewport2D,
    format_coordinate,
)


# Zoom factor applied per standard wheel notch (120 eighths of a degree).
WHEEL_ZOOM_FACTOR = 1.15
WHEEL_NOTCH = 120.0


class Viewport2DViewModel(QObject):
    """Translate 2D canvas input into camera changes and expose screen-space geometry.

    The camera lives in :class:`SceneDocument` and is changed through
    :class:`WorkspaceViewModel`; the viewport size and cursor are presentation
    state owned here. QML only draws the positions this object publishes.
    """

    gridChanged = Signal()
    cursorChanged = Signal()

    def __init__(
        self,
        document: SceneDocument,
        workspace: WorkspaceViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._workspace = workspace
        self._width = 0.0
        self._height = 0.0
        self._cursor: tuple[float, float] | None = None
        self._layout = self._viewport().grid()
        workspace.camera2DChanged.connect(self._refresh)

    def _viewport(self) -> Viewport2D:
        return Viewport2D(self._document.workspace_state_2d, self._width, self._height)

    def _refresh(self) -> None:
        self._layout = self._viewport().grid()
        self.gridChanged.emit()
        if self._cursor is not None:
            self.cursorChanged.emit()

    @property
    def layout(self) -> GridLayout:
        return self._layout

    @Property(float, notify=gridChanged)
    def viewportWidth(self) -> float:
        return self._width

    @Property(float, notify=gridChanged)
    def viewportHeight(self) -> float:
        return self._height

    @Property(float, notify=gridChanged)
    def originX(self) -> float:
        return self._layout.origin_x

    @Property(float, notify=gridChanged)
    def originY(self) -> float:
        return self._layout.origin_y

    @Property("QVariantList", notify=gridChanged)
    def majorX(self) -> list[float]:
        return list(self._layout.major_x)

    @Property("QVariantList", notify=gridChanged)
    def majorY(self) -> list[float]:
        return list(self._layout.major_y)

    @Property("QVariantList", notify=gridChanged)
    def minorX(self) -> list[float]:
        return list(self._layout.minor_x)

    @Property("QVariantList", notify=gridChanged)
    def minorY(self) -> list[float]:
        return list(self._layout.minor_y)

    @Property("QVariantList", notify=gridChanged)
    def xLabels(self) -> list[dict]:
        return [{"position": label.position, "text": label.text} for label in self._layout.x_labels]

    @Property("QVariantList", notify=gridChanged)
    def yLabels(self) -> list[dict]:
        return [{"position": label.position, "text": label.text} for label in self._layout.y_labels]

    @Property(str, notify=gridChanged)
    def cameraSummary(self) -> str:
        camera = self._document.workspace_state_2d
        return (
            f"Center ({format_coordinate(camera.center_x, 2)}, "
            f"{format_coordinate(camera.center_y, 2)}) · Zoom {camera.zoom:.2f}×"
        )

    @Property(str, notify=cursorChanged)
    def cursorText(self) -> str:
        if self._cursor is None:
            return ""
        x, y = self._viewport().to_world(*self._cursor)
        decimals = self._layout.step.label_decimals + 2
        return f"x = {format_coordinate(x, decimals)}, y = {format_coordinate(y, decimals)}"

    @Slot(float, float)
    def setViewportSize(self, width: float, height: float) -> None:
        if not (math.isfinite(width) and math.isfinite(height)):
            return
        width, height = max(width, 0.0), max(height, 0.0)
        if (width, height) != (self._width, self._height):
            self._width, self._height = width, height
            self._refresh()

    @Slot(float, float)
    def panBy(self, delta_x: float, delta_y: float) -> None:
        if not (math.isfinite(delta_x) and math.isfinite(delta_y)):
            return
        self._set_camera(self._viewport().panned(delta_x, delta_y))

    @Slot(float, float, float)
    def zoomAt(self, screen_x: float, screen_y: float, wheel_delta: float) -> None:
        """Zoom around a screen point; ``wheel_delta`` is a Qt wheel angle delta."""
        if not all(math.isfinite(value) for value in (screen_x, screen_y, wheel_delta)):
            return
        factor = WHEEL_ZOOM_FACTOR ** (wheel_delta / WHEEL_NOTCH)
        self._set_camera(self._viewport().zoomed_at(screen_x, screen_y, factor))

    @Slot()
    def resetView(self) -> None:
        self._workspace.resetCamera2D()

    @Slot(float, float)
    def setCursor(self, screen_x: float, screen_y: float) -> None:
        self._cursor = (screen_x, screen_y)
        self.cursorChanged.emit()

    @Slot()
    def clearCursor(self) -> None:
        if self._cursor is not None:
            self._cursor = None
            self.cursorChanged.emit()

    def _set_camera(self, camera) -> None:
        self._workspace.setCamera2D(camera.center_x, camera.center_y, camera.zoom)
