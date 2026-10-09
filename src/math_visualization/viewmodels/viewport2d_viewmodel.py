"""2D viewport view model: grid layout, pan, zoom and cursor readout for QML."""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.math_core.matrix_analysis import analyze
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.math_core.manim_port import I_HAT_COLOR, J_HAT_COLOR
from math_visualization.viewmodels.overlay_sizes import (
    ORIENTATION_ARC_MAX_FRACTION,
    ORIENTATION_ARC_RADIUS_PX,
    ORIENTATION_HEAD_HALF_WIDTH_PX,
    ORIENTATION_HEAD_LENGTH_PX,
)
from math_visualization.viewmodels.scene_objects_viewmodel import SceneObjectsViewModel
from math_visualization.viewmodels.transformation_viewmodel import TransformationViewModel
from math_visualization.viewmodels.workspace_viewmodel import WorkspaceViewModel
from math_visualization.viewport.viewport_2d import (
    GridLayout,
    Viewport2D,
    distance_to_segment,
    format_coordinate,
    snap_to_step,
)
from math_visualization.viewport.transformation_geometry import (
    clip_segment,
    line_through_origin,
    lines_per_side,
    orientation_arc,
    transformed_grid,
    unit_square,
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
    transformationGeometryChanged = Signal()

    def __init__(
        self,
        document: SceneDocument,
        workspace: WorkspaceViewModel,
        scene: SceneObjectsViewModel,
        transformation: TransformationViewModel,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._document = document
        self._workspace = workspace
        self._scene = scene
        self._transformation = transformation
        self._width = 0.0
        self._height = 0.0
        self._cursor: tuple[float, float] | None = None
        self._grab_offset = (0.0, 0.0)
        self._layout = self._viewport().grid()
        workspace.camera2DChanged.connect(self._refresh)
        scene.vectorsChanged.connect(self.vectorShapesChanged)
        scene.selectionChanged.connect(self.vectorShapesChanged)
        for signal in (transformation.currentMatrixChanged, transformation.visualStateChanged):
            signal.connect(self.vectorShapesChanged)
            signal.connect(self.transformationGeometryChanged)
        # The kernel line belongs to the target matrix, which can change while A(t) does not.
        transformation.matrixChanged.connect(self.transformationGeometryChanged)

    def _viewport(self) -> Viewport2D:
        return Viewport2D(self._document.workspace_state_2d, self._width, self._height)

    def _refresh(self) -> None:
        self._layout = self._viewport().grid()
        self.gridChanged.emit()
        self.vectorShapesChanged.emit()
        self.transformationGeometryChanged.emit()
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
        """Screen-space tips of every vector (tails sit at ``originX/originY``).

        ``tipX/tipY`` is the transformed vector A(t)·v. ``ghostX/ghostY`` is the
        input v, drawn faintly while a transformation is applied; it is the
        handle that dragging moves.
        """
        view = self._viewport()
        selected = self._document.selected_object_id
        current = self._transformation.current_matrix()
        show_ghosts = self._document.visual_state.show_ghosts and not self._transformation.is_identity_now
        shapes = []
        for vector in self._document.vectors:
            image = current @ vector.vector
            tip_x, tip_y = view.to_screen(image.x, image.y)
            ghost_x, ghost_y = view.to_screen(vector.vector.x, vector.vector.y)
            shapes.append(
                {
                    "objectId": vector.object_id,
                    "name": vector.name,
                    "color": vector.color,
                    "tipX": tip_x,
                    "tipY": tip_y,
                    "ghostX": ghost_x,
                    "ghostY": ghost_y,
                    "showGhost": show_ghosts,
                    "selected": vector.object_id == selected,
                    "isZero": image.is_zero(),
                }
            )
        return shapes

    @Slot(float, float, result="QVariantMap")
    def hitTest(self, screen_x: float, screen_y: float) -> dict:
        """Return ``{"objectId", "part"}`` where part is ``"tip"``, ``"shaft"`` or ``""``.

        The draggable tip is the input vector (its ghost while transformed);
        either the input or the transformed shaft selects. Tips win over
        shafts, the nearest wins, and the selected vector wins ties.
        """
        view = self._viewport()
        origin = view.to_screen(0.0, 0.0)
        pointer = (screen_x, screen_y)
        selected = self._document.selected_object_id
        current = self._transformation.current_matrix()
        best_tip: tuple[float, bool, str] | None = None
        best_shaft: tuple[float, bool, str] | None = None
        for vector in self._document.vectors:
            tip = view.to_screen(vector.vector.x, vector.vector.y)
            image = current @ vector.vector
            transformed_tip = view.to_screen(image.x, image.y)
            rank_bonus = vector.object_id != selected
            tip_distance = math.hypot(screen_x - tip[0], screen_y - tip[1])
            if tip_distance <= TIP_HIT_RADIUS_PX:
                candidate = (tip_distance, rank_bonus, vector.object_id)
                best_tip = min(best_tip, candidate) if best_tip else candidate
            shaft_distance = min(
                distance_to_segment(pointer, origin, tip),
                distance_to_segment(pointer, origin, transformed_tip),
            )
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

    # Transformation layers ----------------------------------------------------------

    def _screen_segments(self, segments) -> list[float]:
        """Map math segments to screen space and clip them to the viewport (flat list)."""
        view = self._viewport()
        margin = 4.0
        flat: list[float] = []
        for start, end in segments:
            clipped = clip_segment(
                (view.to_screen(*start), view.to_screen(*end)),
                -margin,
                -margin,
                self._width + margin,
                self._height + margin,
            )
            if clipped is not None:
                flat.extend((*clipped[0], *clipped[1]))
        return flat

    def _grid_segments(self):
        radius = self._view_radius()
        step = self._layout.step.major
        current = self._transformation.current_matrix()
        return transformed_grid(current, step, lines_per_side(current, radius, step))

    @Property("QVariantList", notify=transformationGeometryChanged)
    def transformedGridLines(self) -> list[float]:
        """Transformed major grid lines as flat ``[x1, y1, x2, y2, …]`` screen coordinates."""
        if self._width <= 0.0 or self._height <= 0.0:
            return []
        return self._screen_segments(self._grid_segments()[0])

    @Property("QVariantList", notify=transformationGeometryChanged)
    def transformedAxisLines(self) -> list[float]:
        """Images of the x and y axes, flat screen coordinates."""
        if self._width <= 0.0 or self._height <= 0.0:
            return []
        return self._screen_segments(self._grid_segments()[1])

    @Property("QVariantList", notify=transformationGeometryChanged)
    def unitSquare(self) -> list[float]:
        """Corners of A(t)·[0, 1]² as flat screen coordinates (4 points)."""
        view = self._viewport()
        flat: list[float] = []
        for point in unit_square(self._transformation.current_matrix()):
            flat.extend(view.to_screen(*point))
        return flat

    @Property("QVariantList", notify=transformationGeometryChanged)
    def basisVectors(self) -> list[dict]:
        """î and ĵ after A(t): the columns of the current matrix."""
        view = self._viewport()
        current = self._transformation.current_matrix()
        basis = []
        for label, column, color in (
            ("î", current.first_column, I_HAT_COLOR),
            ("ĵ", current.second_column, J_HAT_COLOR),
        ):
            tip_x, tip_y = view.to_screen(column.x, column.y)
            basis.append(
                {"label": label, "color": color, "tipX": tip_x, "tipY": tip_y, "isZero": column.is_zero()}
            )
        return basis

    @Property("QVariantMap", notify=transformationGeometryChanged)
    def determinantOverlay(self) -> dict:
        """Visual feedback for det, orientation and rank, in screen coordinates.

        ``flipped`` and the arc describe A(t); ``imageLine`` / ``collapsedToOrigin``
        show where A(t) squashes the plane when its rank drops; ``kernelLine`` is
        the null space of the target A. Flat lists are empty when not shown.
        """
        view = self._viewport()
        current = self._transformation.current_matrix()
        live = analyze(current)
        target = analyze(self._document.matrix)
        visual = self._document.visual_state
        overlay = {
            "flipped": live.determinant < 0.0 and live.is_invertible,
            "arc": [],
            "arcHead": [],
            "imageLine": [],
            "collapsedToOrigin": live.rank == 0,
            "kernelLine": [],
        }
        label_x, label_y = view.to_screen(*current.apply_point(0.5, 0.5))
        overlay.update(labelX=label_x, labelY=label_y)
        if self._width <= 0.0 or self._height <= 0.0:
            return overlay
        units = 1.0 / view.pixels_per_unit
        if visual.show_orientation_arc:
            shortest = min(current.first_column.length, current.second_column.length)
            arc = orientation_arc(
                current,
                min(ORIENTATION_ARC_RADIUS_PX * units, ORIENTATION_ARC_MAX_FRACTION * shortest),
                ORIENTATION_HEAD_LENGTH_PX * units,
                ORIENTATION_HEAD_HALF_WIDTH_PX * units,
            )
            if arc is not None:
                points, head = arc
                overlay["arc"] = [c for point in points for c in view.to_screen(*point)]
                overlay["arcHead"] = [c for point in head for c in view.to_screen(*point)]
        reach = self._view_radius()
        if live.image_direction is not None:
            direction = live.image_direction
            overlay["imageLine"] = self._screen_segments([line_through_origin((direction.x, direction.y), reach)])
        if visual.show_kernel and target.kernel_direction is not None:
            direction = target.kernel_direction
            overlay["kernelLine"] = self._screen_segments([line_through_origin((direction.x, direction.y), reach)])
        return overlay

    def _view_radius(self) -> float:
        """Distance from the origin to the farthest viewport corner, in math units."""
        view = self._viewport()
        corners = (view.to_world(0.0, 0.0), view.to_world(self._width, self._height),
                   view.to_world(0.0, self._height), view.to_world(self._width, 0.0))
        return max(math.hypot(x, y) for x, y in corners)
