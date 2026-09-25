"""Workspace view model: the 2D/3D mode and each workspace's camera state."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Property, Signal, Slot

from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import (
    CameraState2D,
    CameraState3D,
    WorkspaceMode,
)


class WorkspaceViewModel(QObject):
    """Expose workspace state stored in :class:`SceneDocument` to QML.

    Switching workspaces only changes ``workspace_mode``; the document and the
    camera state of the inactive workspace are left untouched.
    """

    workspaceModeChanged = Signal()
    camera2DChanged = Signal()
    camera3DChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, document: SceneDocument, parent: QObject | None = None):
        super().__init__(parent)
        self._document = document

    @Property(str, notify=workspaceModeChanged)
    def workspaceMode(self) -> str:
        return self._document.workspace_mode.value

    @Property("QVariantMap", notify=camera2DChanged)
    def camera2D(self) -> dict:
        camera = self._document.workspace_state_2d
        return {"centerX": camera.center_x, "centerY": camera.center_y, "zoom": camera.zoom}

    @Property("QVariantMap", notify=camera3DChanged)
    def camera3D(self) -> dict:
        camera = self._document.workspace_state_3d
        return {
            "targetX": camera.target_x,
            "targetY": camera.target_y,
            "targetZ": camera.target_z,
            "azimuth": camera.azimuth,
            "elevation": camera.elevation,
            "distance": camera.distance,
            "projectionMode": camera.projection_mode.value,
        }

    @Slot(str)
    def setWorkspaceMode(self, mode: str) -> None:
        try:
            new_mode = WorkspaceMode(mode)
        except ValueError:
            self.errorOccurred.emit(f"Unknown workspace mode: {mode!r}")
            return
        if new_mode is self._document.workspace_mode:
            return
        self._document.workspace_mode = new_mode
        self.workspaceModeChanged.emit()

    @Slot(float, float, float)
    def setCamera2D(self, center_x: float, center_y: float, zoom: float) -> None:
        self._apply_camera_2d(
            lambda: CameraState2D(center_x=center_x, center_y=center_y, zoom=zoom)
        )

    @Slot()
    def resetCamera2D(self) -> None:
        self._apply_camera_2d(CameraState2D)

    @Slot(float, float, float, float, float, float)
    def setCamera3D(
        self,
        target_x: float,
        target_y: float,
        target_z: float,
        azimuth: float,
        elevation: float,
        distance: float,
    ) -> None:
        self._apply_camera_3d(
            lambda: replace(
                self._document.workspace_state_3d,
                target_x=target_x,
                target_y=target_y,
                target_z=target_z,
                azimuth=azimuth,
                elevation=elevation,
                distance=distance,
            )
        )

    @Slot(str)
    def setProjectionMode3D(self, mode: str) -> None:
        self._apply_camera_3d(
            lambda: replace(self._document.workspace_state_3d, projection_mode=mode)
        )

    @Slot()
    def resetCamera3D(self) -> None:
        self._apply_camera_3d(CameraState3D)

    def _apply_camera_2d(self, build) -> None:
        try:
            camera = build()
        except ValueError as error:
            self.errorOccurred.emit(f"Invalid 2D camera: {error}")
            return
        if camera != self._document.workspace_state_2d:
            self._document.workspace_state_2d = camera
            self.camera2DChanged.emit()

    def _apply_camera_3d(self, build) -> None:
        try:
            camera = build()
        except ValueError as error:
            self.errorOccurred.emit(f"Invalid 3D camera: {error}")
            return
        if camera != self._document.workspace_state_3d:
            self._document.workspace_state_3d = camera
            self.camera3DChanged.emit()
