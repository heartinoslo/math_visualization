"""2D viewport view model: grid layout, pan, zoom and cursor readout for QML."""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.scene_objects_viewmodel import SceneObjectsViewModel
from math_visualization.viewmodels.workspace_viewmodel import WorkspaceViewModel
from math_visualization.viewport.viewport_2d import (
    GridLayout,
    Viewport2D,
    distance_to_segment,
    format_coordinate,
    snap_to_step,
)


# Zoom factor applied per standard wheel notch (120 eighths of a degree).
WHEEL_ZOOM_FACTOR = 1.15
WHEEL_NOTCH = 120.0
# Pointer tolerances for picking a vector's tip (to drag it) or shaft (to select it).
TIP_HIT_RADIUS_PX = 12.0
SHAFT_HIT_DISTANCE_PX = 6.0


class Viewport2DViewModel(QObject):
    """Translate 2D canvas input into camera changes and expose screen-space geometry.

    The camera lives in :class:`SceneDocument` and is changed through
    :class:`WorkspaceViewModel`; the viewport size and cursor are presentation
    state owned here. QML only draws the positions this object publishes.
    """

    gridChanged = Signal()
    cursorChanged = Signal()
    vectorShapesChanged = Signal()

    def __init__(
        self,
        document: SceneDocument,
        workspace: WorkspaceViewModel,
        scene: SceneObjectsViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._workspace = workspace
        self._scene = scene
        self._width = 0.0
        self._height = 0.0
        self._cursor: tuple[float, float] | None = None
        self._grab_offset = (0.0, 0.0)
        self._layout = self._viewport().grid()
        workspace.camera2DChanged.connect(self._refresh)
        scene.vectorsChanged.connect(self.vectorShapesChanged)
        scene.selectionChanged.connect(self.vectorShapesChanged)

    def _viewport(self) -> Viewport2D:
        return Viewport2D(self._document.workspace_state_2d, self._width, self._height)

    def _refresh(self) -> None:
        self._layout = self._viewport().grid()
        self.gridChanged.emit()
        self.vectorShapesChanged.emit()
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

    # Vectors ------------------------------------------------------------------

    @Property("QVariantList", notify=vectorShapesChanged)
    def vectorShapes(self) -> list[dict]:
        """Screen-space tip of every vector (tails sit at ``originX/originY``)."""
        view = self._viewport()
        selected = self._document.selected_object_id
        shapes = []
        for vector in self._document.vectors:
            tip_x, tip_y = view.to_screen(vector.vector.x, vector.vector.y)
            shapes.append(
                {
                    "objectId": vector.object_id,
                    "name": vector.name,
                    "color": vector.color,
                    "tipX": tip_x,
                    "tipY": tip_y,
                    "selected": vector.object_id == selected,
                    "isZero": vector.vector.is_zero(),
                }
            )
        return shapes

    @Slot(float, float, result="QVariantMap")
    def hitTest(self, screen_x: float, screen_y: float) -> dict:
        """Return ``{"objectId", "part"}`` where part is ``"tip"``, ``"shaft"`` or ``""``.

        Tips win over shafts, the nearest tip wins, and the selected vector wins ties.
        """
        view = self._viewport()
        origin = view.to_screen(0.0, 0.0)
        pointer = (screen_x, screen_y)
        selected = self._document.selected_object_id
        best_tip: tuple[float, bool, str] | None = None
        best_shaft: tuple[float, bool, str] | None = None
        for vector in self._document.vectors:
            tip = view.to_screen(vector.vector.x, vector.vector.y)
            rank_bonus = vector.object_id != selected
            tip_distance = math.hypot(screen_x - tip[0], screen_y - tip[1])
            if tip_distance <= TIP_HIT_RADIUS_PX:
                candidate = (tip_distance, rank_bonus, vector.object_id)
                best_tip = min(best_tip, candidate) if best_tip else candidate
            shaft_distance = distance_to_segment(pointer, origin, tip)
            if shaft_distance <= SHAFT_HIT_DISTANCE_PX:
                candidate = (shaft_distance, rank_bonus, vector.object_id)
                best_shaft = min(best_shaft, candidate) if best_shaft else candidate
        if best_tip:
            return {"objectId": best_tip[2], "part": "tip"}
        if best_shaft:
            return {"objectId": best_shaft[2], "part": "shaft"}
        return {"objectId": "", "part": ""}

    @Slot(float, float, result=str)
    def beginVectorDrag(self, screen_x: float, screen_y: float) -> str:
        """Handle a press: select a hit vector and start dragging it if its tip was hit.

        Returns the hit part so QML can fall back to panning on empty space.
        """
        hit = self.hitTest(screen_x, screen_y)
        if hit["part"] == "tip":
            vector = self._document.find_vector(hit["objectId"])
            pointer_x, pointer_y = self._viewport().to_world(screen_x, screen_y)
            # Keep the tip where it is relative to the pointer, so it never jumps.
            self._grab_offset = (vector.vector.x - pointer_x, vector.vector.y - pointer_y)
            self._scene.beginDrag(hit["objectId"])
        elif hit["part"] == "shaft":
            self._scene.select(hit["objectId"])
        return hit["part"]

    @Slot(float, float, bool)
    def dragVector(self, screen_x: float, screen_y: float, snap: bool) -> None:
        """Move the dragged tip under the pointer, optionally snapping to the minor grid."""
        if not self._scene.dragging or not (math.isfinite(screen_x) and math.isfinite(screen_y)):
            return
        x, y = self._viewport().to_world(screen_x, screen_y)
        x += self._grab_offset[0]
        y += self._grab_offset[1]
        if snap:
            step = self._layout.step.minor
            x, y = snap_to_step(x, step), snap_to_step(y, step)
        self._scene.dragTo(x, y)

    @Slot()
    def endVectorDrag(self) -> None:
        self._scene.endDrag()
