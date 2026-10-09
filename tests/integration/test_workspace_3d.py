"""Integration coverage for the Stage 3 workspace: input, bindings and rendering."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QWheelEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow, QSGRendererInterface
from PySide6.QtTest import QTest

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import CameraState3D
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def load_3d_shell():
    application = create_gui_application(["pytest"])
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    engine = QQmlApplicationEngine()
    assert load_main_qml(engine, view_model)
    window = engine.rootObjects()[0]
    view_model.workspace.setWorkspaceMode("3d")
    application.processEvents()
    return application, document, view_model, engine, window


def canvas_point(window, x: float, y: float) -> QPoint:
    area = window.findChild(QQuickItem, "viewport3DPointerArea")
    return area.mapToScene(QPointF(x, y)).toPoint()


def drag(window, application, button, delta: QPoint, modifier=Qt.NoModifier) -> None:
    start = canvas_point(window, 300, 200)
    QTest.mousePress(window, button, modifier, start)
    QTest.mouseMove(window, start + delta / 2)
    QTest.mouseMove(window, start + delta)
    QTest.mouseRelease(window, button, modifier, start + delta)
    application.processEvents()


def click(window, object_name: str, application) -> None:
    assert QMetaObject.invokeMethod(window.findChild(QObject, object_name), "click")
    application.processEvents()


def test_scene_binds_camera_and_reports_canvas_size() -> None:
    application, _, view_model, engine, window = load_3d_shell()
    viewport = view_model.viewport3D
    canvas = window.findChild(QQuickItem, "workspace3D")
    camera = window.findChild(QObject, "perspectiveCamera")

    assert (viewport.viewport().width, viewport.viewport().height) == (canvas.width(), canvas.height())
    assert window.findChild(QObject, "view3D").property("activeCameraName") == "perspectiveCamera"
    assert camera.property("position") == viewport.cameraPosition
    assert window.findChild(QObject, "labels3D").property("count") == len(viewport.labels)
    hint = window.findChild(QObject, "dimensionHintLabel").property("text")
    assert hint == "Mathematical dimension: 2D · Display workspace: 3D · Active plane: XY"


def test_right_drag_orbits_and_leaves_target_and_distance() -> None:
    application, document, view_model, engine, window = load_3d_shell()

    drag(window, application, Qt.RightButton, QPoint(50, -20))

    camera = document.workspace_state_3d
    assert camera.azimuth == pytest.approx(-60.0 - 50 * 0.3)
    assert camera.elevation == pytest.approx(25.0 - 20 * 0.3)
    assert (camera.target_x, camera.target_y, camera.distance) == (0.0, 0.0, 12.0)


@pytest.mark.parametrize(
    ("button", "modifier"),
    [(Qt.MiddleButton, Qt.NoModifier), (Qt.RightButton, Qt.ShiftModifier)],
)
def test_middle_or_shift_right_drag_pans(button, modifier) -> None:
    application, document, view_model, engine, window = load_3d_shell()

    drag(window, application, button, QPoint(60, 30), modifier)

    camera = document.workspace_state_3d
    assert (camera.azimuth, camera.elevation) == (-60.0, 25.0)
    assert (camera.target_x, camera.target_y) != (0.0, 0.0)


def test_left_drag_is_reserved_for_objects() -> None:
    application, document, view_model, engine, window = load_3d_shell()

    drag(window, application, Qt.LeftButton, QPoint(60, 30))

    assert document.workspace_state_3d == CameraState3D()


def test_wheel_zoom_double_click_and_keyboard_presets() -> None:
    application, document, view_model, engine, window = load_3d_shell()
    position = QPointF(canvas_point(window, 200, 200))
    wheel = QWheelEvent(
        position, window.mapToGlobal(position), QPoint(), QPoint(0, 120),
        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
    )
    QGuiApplication.sendEvent(window, wheel)
    application.processEvents()
    assert document.workspace_state_3d.distance == pytest.approx(12.0 / 1.15)

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position.toPoint())
    QTest.keyClick(window, Qt.Key_2)
    application.processEvents()
    assert document.workspace_state_3d.elevation == 89.0
    QTest.keyClick(window, Qt.Key_1)
    application.processEvents()
    assert (document.workspace_state_3d.azimuth, document.workspace_state_3d.elevation) == (-90.0, 0.0)

    QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, position.toPoint())
    application.processEvents()
    assert document.workspace_state_3d == CameraState3D()


def test_toolbar_and_header_controls() -> None:
    application, document, view_model, engine, window = load_3d_shell()

    click(window, "topViewButton", application)
    assert document.workspace_state_3d.elevation == 89.0
    click(window, "projectionButton", application)
    assert window.findChild(QObject, "view3D").property("activeCameraName") == "orthographicCamera"
    click(window, "auxiliaryPlanesButton", application)
    assert window.findChild(QObject, "auxiliaryGrid").property("visible") is False
    click(window, "resetViewButton", application)
    assert document.workspace_state_3d == CameraState3D()


def test_status_bar_shows_camera_and_picked_plane_point() -> None:
    application, _, view_model, engine, window = load_3d_shell()
    viewport = view_model.viewport3D
    centre = canvas_point(window, viewport.viewport().width / 2, viewport.viewport().height / 2)

    QTest.mouseMove(window, centre)
    application.processEvents()

    summary = window.findChild(QObject, "camera3DSummary").property("text")
    cursor = window.findChild(QObject, "cursor3DCoordinates").property("text")
    assert summary == "Azimuth -60° · Elevation 25° · Distance 12.00 · Perspective"
    assert cursor.startswith("XY plane: x = ")


def rhi_available(window) -> bool:
    interface = window.rendererInterface()
    return interface is not None and QSGRendererInterface.isApiRhiBased(interface.graphicsApi())


def test_rendered_axes_match_python_projection() -> None:
    """Python's projection and Qt Quick 3D's rendering must agree pixel-wise.

    Needs a GPU-capable platform (for example ``QT_QPA_PLATFORM=xcb`` under
    ``xvfb-run``); the offscreen platform cannot render Qt Quick 3D.
    """
    application, _, view_model, engine, window = load_3d_shell()
    if not rhi_available(window):
        pytest.skip("Qt Quick 3D needs an RHI-based graphics API")
    for _ in range(10):
        application.processEvents()
    image = QQuickWindow.grabWindow(window)
    canvas = window.findChild(QQuickItem, "workspace3D")
    view = view_model.viewport3D.viewport()
    ratio = image.width() / window.width()

    def pixel(point) -> QColor:
        projected = view.project(point)
        scene = canvas.mapToScene(QPointF(projected.x, projected.y))
        return image.pixelColor(round(scene.x() * ratio), round(scene.y() * ratio))

    # 3Blue1Brown style: the axes are a bright neutral grey (or the white
    # transformed axes drawn over them), never the dark background.
    # Sample between major lines so the blue transformed grid, which crosses
    # the axes at them, does not blend into the pixel.
    tip = view.axis_half_length
    # Also stay clear of î, ĵ and the unit square, which lie on the axes up to 1.
    between = view.grid().step.major * 1.5
    for point in ((between, 0.0, 0.0), (0.0, between, 0.0), (0.0, 0.0, tip * 0.5)):
        colour = pixel(point)
        assert min(colour.red(), colour.green(), colour.blue()) > 150, point
        assert max(colour.red(), colour.green(), colour.blue()) - min(
            colour.red(), colour.green(), colour.blue()
        ) < 30, point
