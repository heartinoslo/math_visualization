"""3D viewport view model: orbit camera, grids, labels and active-plane picking."""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QQuaternion, QVector3D

from math_visualization.rendering.line_geometry import LineSetGeometry
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import ProjectionMode
from math_visualization.viewmodels.scene_objects_viewmodel import SceneObjectsViewModel
from math_visualization.viewmodels.workspace_viewmodel import WorkspaceViewModel
from math_visualization.viewport.viewport_2d import distance_to_segment, format_coordinate, snap_to_step
from math_visualization.viewport.viewport_3d import (
    AUXILIARY_HALF_EXTENT_MAJORS,
    CAMERA_PRESETS,
    FIELD_OF_VIEW_DEGREES,
    SCENE_UNITS_PER_MATH_UNIT,
    Grid3D,
    Viewport3D,
    grid_positions,
    math_to_scene,
    plane_segments,
)


# Axis thickness stays roughly constant on screen by scaling with distance.
AXIS_RADIUS_PER_DISTANCE = 0.0022
# Tick labels closer than this on screen are dropped so they never overlap.
MIN_TICK_LABEL_SPACING_PX = 28.0
# Vector arrows, relative to the camera distance so they keep their screen size.
VECTOR_RADIUS_PER_DISTANCE = 0.0040
SELECTED_VECTOR_RADIUS_PER_DISTANCE = 0.0058
VECTOR_HEAD_LENGTH_PER_DISTANCE = 0.045
TIP_HIT_RADIUS_PX = 14.0
SHAFT_HIT_DISTANCE_PX = 6.0


class Viewport3DViewModel(QObject):
    """Translate 3D canvas input into camera changes and expose scene data to QML.

    The camera lives in :class:`SceneDocument` and is changed through
    :class:`WorkspaceViewModel`. Viewport size, cursor and the auxiliary-plane
    toggle are presentation state owned here. Grid geometry is rebuilt only
    when the grid spacing or centre changes, not on every camera movement.
    """

    cameraChanged = Signal()
    gridChanged = Signal()
    cursorChanged = Signal()
    auxiliaryPlanesVisibleChanged = Signal()
    vectorSceneChanged = Signal()
    errorOccurred = Signal(str)

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
        self._grab_offset = (0.0, 0.0)
        self._width = 0.0
        self._height = 0.0
        self._cursor: tuple[float, float] | None = None
        self._auxiliary_planes_visible = True
        self._grid: Grid3D | None = None
        # QQuick3DGeometry only accepts 3D-object parents; this view model owns
        # the geometries through these references and outlives the QML engine.
        self._minor_grid = LineSetGeometry()
        self._major_grid = LineSetGeometry()
        self._auxiliary_grid = LineSetGeometry()
        self._component_lines = LineSetGeometry()
        workspace.camera3DChanged.connect(self._refresh)
        scene.vectorsChanged.connect(self._on_vectors_changed)
        scene.selectionChanged.connect(self._on_vectors_changed)
        self._refresh()
        self._on_vectors_changed()

    # State ------------------------------------------------------------------

    def viewport(self) -> Viewport3D:
        return Viewport3D(self._document.workspace_state_3d, self._width, self._height)

    def _refresh(self) -> None:
        grid = self.viewport().grid()
        if grid != self._grid:
            self._grid = grid
            self._rebuild_grid(grid)
            self.gridChanged.emit()
        self.cameraChanged.emit()
        # Arrow thickness and label positions depend on the camera.
        self.vectorSceneChanged.emit()
        if self._cursor is not None:
            self.cursorChanged.emit()

    def _on_vectors_changed(self) -> None:
        selected = self._scene.selected_vector
        if selected is None or selected.vector.is_zero():
            self._component_lines.set_segments([])
        else:
            x, y = selected.vector.x, selected.vector.y
            self._component_lines.set_segments(
                [((x, y, 0.0), (x, 0.0, 0.0)), ((x, y, 0.0), (0.0, y, 0.0))]
            )
        self.vectorSceneChanged.emit()

    def _rebuild_grid(self, grid: Grid3D) -> None:
        step = grid.step
        center = (grid.center_x, grid.center_y)
        self._minor_grid.set_segments(
            plane_segments("xy", center, grid.half_extent, step.minor, skip_every=step.subdivisions)
        )
        self._major_grid.set_segments(plane_segments("xy", center, grid.half_extent, step.major))
        auxiliary_extent = step.major * AUXILIARY_HALF_EXTENT_MAJORS
        self._auxiliary_grid.set_segments(
            plane_segments("xz", (grid.center_x, 0.0), auxiliary_extent, step.major)
            + plane_segments("yz", (grid.center_y, 0.0), auxiliary_extent, step.major)
        )

    # Geometry for QML ---------------------------------------------------------

    @Property(QObject, constant=True)
    def minorGridGeometry(self) -> LineSetGeometry:
        return self._minor_grid

    @Property(QObject, constant=True)
    def majorGridGeometry(self) -> LineSetGeometry:
        return self._major_grid

    @Property(QObject, constant=True)
    def auxiliaryGridGeometry(self) -> LineSetGeometry:
        return self._auxiliary_grid

    @Property(float, notify=gridChanged)
    def gridHalfExtent(self) -> float:
        """Half the side of the active-plane grid, in scene units."""
        return self._grid.half_extent * SCENE_UNITS_PER_MATH_UNIT

    @Property(QVector3D, notify=gridChanged)
    def gridCenter(self) -> QVector3D:
        return QVector3D(
            self._grid.center_x * SCENE_UNITS_PER_MATH_UNIT,
            0.0,
            -self._grid.center_y * SCENE_UNITS_PER_MATH_UNIT,
        )

    # Camera for QML -----------------------------------------------------------

    @Property(float, constant=True)
    def fieldOfView(self) -> float:
        return FIELD_OF_VIEW_DEGREES

    @Property(QVector3D, notify=cameraChanged)
    def cameraPosition(self) -> QVector3D:
        return QVector3D(*self.viewport().scene_position)

    @Property(QQuaternion, notify=cameraChanged)
    def cameraRotation(self) -> QQuaternion:
        return QQuaternion(*self.viewport().scene_rotation)

    @Property(float, notify=cameraChanged)
    def clipNear(self) -> float:
        return self.viewport().clip_near

    @Property(float, notify=cameraChanged)
    def clipFar(self) -> float:
        return self.viewport().clip_far

    @Property(float, notify=cameraChanged)
    def orthographicMagnification(self) -> float:
        return self.viewport().orthographic_magnification

    @Property(str, notify=cameraChanged)
    def projectionMode(self) -> str:
        return self._document.workspace_state_3d.projection_mode.value

    @Property(float, notify=cameraChanged)
    def axisRadius(self) -> float:
        """Axis thickness in scene units, proportional to the camera distance."""
        return self.viewport().distance * AXIS_RADIUS_PER_DISTANCE * SCENE_UNITS_PER_MATH_UNIT

    @Property(str, notify=cameraChanged)
    def cameraSummary(self) -> str:
        camera = self._document.workspace_state_3d
        view = self.viewport()
        return (
            f"Azimuth {camera.azimuth:.0f}° · Elevation {view.elevation:.0f}° · "
            f"Distance {view.distance:.2f} · {camera.projection_mode.value.capitalize()}"
        )

    @Property(float, notify=cameraChanged)
    def axisHalfLength(self) -> float:
        return self.viewport().axis_half_length * SCENE_UNITS_PER_MATH_UNIT

    @Property("QVariantList", notify=cameraChanged)
    def labels(self) -> list[dict]:
        """Screen positions of axis names and major tick labels on the x and y axes.

        Each entry has ``text``, ``kind`` (``"axis"`` or ``"tick"``), ``axis``
        (``"x"``, ``"y"`` or ``"z"``) and screen ``x`` / ``y``.
        """
        view = self.viewport()
        if view.width <= 0.0 or view.height <= 0.0:
            return []
        entries: list[dict] = []
        tip = view.axis_half_length
        for name, point in (("x", (tip, 0.0, 0.0)), ("y", (0.0, tip, 0.0)), ("z", (0.0, 0.0, tip))):
            entries.append(self._label(view, point, name, "axis", name))
        step = self._grid.step
        for axis in (0, 1):
            placed: list[dict] = []
            # Nearest ticks first, so crowding near the horizon drops the far ones.
            values = sorted(grid_positions(0.0, tip, step.major), key=abs)
            for value in values:
                if abs(value) > tip * (1.0 - 1e-9):
                    continue
                point = (value, 0.0, 0.0) if axis == 0 else (0.0, value, 0.0)
                text = format_coordinate(value, step.label_decimals)
                label = self._label(view, point, text, "tick", "xy"[axis])
                if label["visible"] and all(
                    math.hypot(label["x"] - other["x"], label["y"] - other["y"]) >= MIN_TICK_LABEL_SPACING_PX
                    for other in placed
                ):
                    placed.append(label)
            entries.extend(placed)
        return [entry for entry in entries if entry["visible"]]

    @staticmethod
    def _label(view: Viewport3D, point, text: str, kind: str, axis: str) -> dict:
        projection = view.project(point)
        inside = 0.0 <= projection.x <= view.width and 0.0 <= projection.y <= view.height
        return {
            "text": text,
            "kind": kind,
            "axis": axis,
            "x": projection.x,
            "y": projection.y,
            "visible": projection.visible and inside,
        }

    # Cursor and picking -----------------------------------------------------------

    @Property(str, notify=cursorChanged)
    def cursorText(self) -> str:
        if self._cursor is None:
            return ""
        point = self.viewport().pick_active_plane(*self._cursor)
        if point is None:
            return ""
        decimals = self._grid.step.label_decimals + 2
        return (
            f"XY plane: x = {format_coordinate(point[0], decimals)}, "
            f"y = {format_coordinate(point[1], decimals)}"
        )

    @Slot(float, float, result="QVariantMap")
    def pickActivePlane(self, screen_x: float, screen_y: float) -> dict:
        """Return ``{"hit", "x", "y"}`` for the pointer ray against the XY plane."""
        point = self.viewport().pick_active_plane(screen_x, screen_y)
        if point is None:
            return {"hit": False, "x": 0.0, "y": 0.0}
        return {"hit": True, "x": point[0], "y": point[1]}

    @Slot(float, float)
    def setCursor(self, screen_x: float, screen_y: float) -> None:
        self._cursor = (screen_x, screen_y)
        self.cursorChanged.emit()

    @Slot()
    def clearCursor(self) -> None:
        if self._cursor is not None:
            self._cursor = None
            self.cursorChanged.emit()

    # Presentation toggles -------------------------------------------------------

    @Property(bool, notify=auxiliaryPlanesVisibleChanged)
    def auxiliaryPlanesVisible(self) -> bool:
        return self._auxiliary_planes_visible

    @Slot()
    def toggleAuxiliaryPlanes(self) -> None:
        self._auxiliary_planes_visible = not self._auxiliary_planes_visible
        self.auxiliaryPlanesVisibleChanged.emit()

    # Input ------------------------------------------------------------------------

    @Slot(float, float)
    def setViewportSize(self, width: float, height: float) -> None:
        if not (math.isfinite(width) and math.isfinite(height)):
            return
        width, height = max(width, 0.0), max(height, 0.0)
        if (width, height) != (self._width, self._height):
            self._width, self._height = width, height
            self._refresh()

    @Slot(float, float)
    def orbitBy(self, delta_x: float, delta_y: float) -> None:
        if math.isfinite(delta_x) and math.isfinite(delta_y):
            self._set_camera(self.viewport().orbited(delta_x, delta_y))

    @Slot(float, float)
    def panBy(self, delta_x: float, delta_y: float) -> None:
        if math.isfinite(delta_x) and math.isfinite(delta_y):
            self._set_camera(self.viewport().panned(delta_x, delta_y))

    @Slot(float)
    def zoomBy(self, wheel_delta: float) -> None:
        """Dolly towards the target; ``wheel_delta`` is a Qt wheel angle delta."""
        if math.isfinite(wheel_delta):
            self._set_camera(self.viewport().zoomed(wheel_delta))

    @Slot(str)
    def applyPreset(self, name: str) -> None:
        if name not in CAMERA_PRESETS:
            self.errorOccurred.emit(f"Unknown camera preset: {name!r}")
            return
        self._set_camera(self.viewport().with_preset(name))

    @Slot()
    def toggleProjectionMode(self) -> None:
        current = self._document.workspace_state_3d.projection_mode
        next_mode = (
            ProjectionMode.ORTHOGRAPHIC
            if current is ProjectionMode.PERSPECTIVE
            else ProjectionMode.PERSPECTIVE
        )
        self._workspace.setProjectionMode3D(next_mode.value)

    @Slot()
    def resetView(self) -> None:
        self._workspace.resetCamera3D()

    def _set_camera(self, camera) -> None:
        self._workspace.setCamera3D(
            camera.target_x,
            camera.target_y,
            camera.target_z,
            camera.azimuth,
            camera.elevation,
            camera.distance,
        )

    # Vectors ------------------------------------------------------------------

    @Property(QObject, constant=True)
    def componentLinesGeometry(self) -> LineSetGeometry:
        """Helper lines from the selected vector's tip to the x and y axes."""
        return self._component_lines

    @Property(bool, notify=vectorSceneChanged)
    def componentLinesVisible(self) -> bool:
        selected = self._scene.selected_vector
        return selected is not None and not selected.vector.is_zero()

    @Property("QVariantList", notify=vectorSceneChanged)
    def vectorArrows(self) -> list[dict]:
        """Scene transforms of each vector arrow, embedded in the XY plane as (x, y, 0).

        Each arrow node points its local +Y along the vector; the shaft and the
        head are sized from the camera distance so they keep a steady on-screen
        thickness, and short vectors shrink their head instead of overshooting.
        """
        view = self.viewport()
        distance = view.distance
        selected_id = self._document.selected_object_id
        arrows = []
        for vector in self._document.vectors:
            selected = vector.object_id == selected_id
            radius = distance * (SELECTED_VECTOR_RADIUS_PER_DISTANCE if selected else VECTOR_RADIUS_PER_DISTANCE)
            length = vector.vector.length
            head = min(distance * VECTOR_HEAD_LENGTH_PER_DISTANCE, 0.5 * length)
            if vector.vector.is_zero():
                rotation = QQuaternion()
            else:
                direction = QVector3D(*math_to_scene((vector.vector.x, vector.vector.y, 0.0))).normalized()
                rotation = QQuaternion.rotationTo(QVector3D(0.0, 1.0, 0.0), direction)
            arrows.append(
                {
                    "objectId": vector.object_id,
                    "color": vector.color,
                    "selected": selected,
                    "isZero": vector.vector.is_zero(),
                    "rotation": rotation,
                    "shaftLength": (length - head) * SCENE_UNITS_PER_MATH_UNIT,
                    "headLength": head * SCENE_UNITS_PER_MATH_UNIT,
                    "radius": radius * SCENE_UNITS_PER_MATH_UNIT,
                    "headRadius": max(radius * 2.6, head * 0.3) * SCENE_UNITS_PER_MATH_UNIT,
                }
            )
        return arrows

    @Property("QVariantList", notify=vectorSceneChanged)
    def vectorLabels(self) -> list[dict]:
        """Screen positions of vector names at their tips."""
        view = self.viewport()
        if view.width <= 0.0 or view.height <= 0.0:
            return []
        labels = []
        for vector in self._document.vectors:
            projection = view.project((vector.vector.x, vector.vector.y, 0.0))
            if projection.visible:
                labels.append(
                    {
                        "name": vector.name,
                        "color": vector.color,
                        "x": projection.x,
                        "y": projection.y,
                        "selected": vector.object_id == self._document.selected_object_id,
                    }
                )
        return labels

    @Slot(float, float, result="QVariantMap")
    def hitTest(self, screen_x: float, screen_y: float) -> dict:
        """Return ``{"objectId", "part"}`` using the projected tips and shafts."""
        view = self.viewport()
        origin = view.project((0.0, 0.0, 0.0))
        pointer = (screen_x, screen_y)
        selected = self._document.selected_object_id
        best_tip = best_shaft = None
        for vector in self._document.vectors:
            tip = view.project((vector.vector.x, vector.vector.y, 0.0))
            if not tip.visible:
                continue
            rank = vector.object_id != selected
            tip_distance = math.hypot(screen_x - tip.x, screen_y - tip.y)
            if tip_distance <= TIP_HIT_RADIUS_PX:
                candidate = (tip_distance, rank, vector.object_id)
                best_tip = min(best_tip, candidate) if best_tip else candidate
            if origin.visible:
                shaft_distance = distance_to_segment(pointer, (origin.x, origin.y), (tip.x, tip.y))
                if shaft_distance <= SHAFT_HIT_DISTANCE_PX:
                    candidate = (shaft_distance, rank, vector.object_id)
                    best_shaft = min(best_shaft, candidate) if best_shaft else candidate
        if best_tip:
            return {"objectId": best_tip[2], "part": "tip"}
        if best_shaft:
            return {"objectId": best_shaft[2], "part": "shaft"}
        return {"objectId": "", "part": ""}

    @Slot(float, float, result=str)
    def beginVectorDrag(self, screen_x: float, screen_y: float) -> str:
        """Select a hit vector and start dragging it when its tip was hit."""
        hit = self.hitTest(screen_x, screen_y)
        if hit["part"] == "tip":
            vector = self._document.find_vector(hit["objectId"])
            picked = self.viewport().pick_active_plane(screen_x, screen_y)
            if picked is None:
                self._scene.select(hit["objectId"])
                return "shaft"
            self._grab_offset = (vector.vector.x - picked[0], vector.vector.y - picked[1])
            self._scene.beginDrag(hit["objectId"])
        elif hit["part"] == "shaft":
            self._scene.select(hit["objectId"])
        return hit["part"]

    @Slot(float, float, bool)
    def dragVector(self, screen_x: float, screen_y: float, snap: bool) -> None:
        """Move the dragged tip to where the pointer ray meets the XY plane.

        Intersecting with ``z = 0`` is what keeps the vector in the active
        plane from any camera angle; rays that miss the plane are ignored.
        """
        if not self._scene.dragging or not (math.isfinite(screen_x) and math.isfinite(screen_y)):
            return
        picked = self.viewport().pick_active_plane(screen_x, screen_y)
        if picked is None:
            return
        x = picked[0] + self._grab_offset[0]
        y = picked[1] + self._grab_offset[1]
        if snap:
            step = self._grid.step.minor
            x, y = snap_to_step(x, step), snap_to_step(y, step)
        self._scene.dragTo(x, y)

    @Slot()
    def endVectorDrag(self) -> None:
        self._scene.endDrag()
