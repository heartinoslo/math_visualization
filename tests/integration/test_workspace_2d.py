"""Offscreen integration coverage for the Stage 2 coordinate canvas."""

from __future__ import annotations

import math

from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QWheelEvent
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.infrastructure.paths import QML_DIRECTORY
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import CameraState2D
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def load_shell():
    application = create_gui_application(["pytest"])
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    engine = QQmlApplicationEngine()
    assert load_main_qml(engine, view_model)
    window = engine.rootObjects()[0]
    application.processEvents()
    return application, document, view_model, engine, window


def canvas_point(window, x: float, y: float) -> QPoint:
    """Map a point in canvas coordinates to window coordinates."""
    area = window.findChild(QQuickItem, "viewportPointerArea")
    return area.mapToScene(QPointF(x, y)).toPoint()


def repeater_count(window, object_name: str) -> int:
    return window.findChild(QObject, object_name).property("count")


def test_canvas_reports_its_size_and_draws_grid_axes_and_labels() -> None:
    application, _, view_model, engine, window = load_shell()
    viewport = view_model.viewport2D
    canvas = window.findChild(QQuickItem, "workspace2D")

    assert viewport.viewportWidth == canvas.width()
    assert viewport.viewportHeight == canvas.height()
    assert repeater_count(window, "majorVerticalLines") == len(viewport.majorX) > 0
    assert repeater_count(window, "minorHorizontalLines") == len(viewport.minorY) > 0
    assert repeater_count(window, "xAxisLabels") == len(viewport.xLabels)
    assert window.findChild(QObject, "xAxis").property("visible") is True
    assert window.findChild(QObject, "yAxis").property("visible") is True


def test_drag_pans_the_view() -> None:
    application, document, view_model, engine, window = load_shell()
    viewport = view_model.viewport2D
    start = canvas_point(window, viewport.viewportWidth / 2, viewport.viewportHeight / 2)
    end = start + QPoint(80, 40)

    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(window, start + QPoint(40, 20))
    QTest.mouseMove(window, end)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, end)
    application.processEvents()

    camera = document.workspace_state_2d
    assert math.isclose(camera.center_x, -1.0)
    assert math.isclose(camera.center_y, 0.5)
    assert camera.zoom == 1.0
    assert "Center (-1.00, 0.50)" in window.findChild(QObject, "camera2DSummary").property("text")


def test_wheel_zooms_around_the_pointer() -> None:
    application, document, view_model, engine, window = load_shell()
    viewport = view_model.viewport2D
    local = (viewport.viewportWidth / 2 + 120, viewport.viewportHeight / 2 - 60)
    position = QPointF(canvas_point(window, *local))
    QTest.mouseMove(window, position.toPoint())
    application.processEvents()
    before = viewport.cursorText

    event = QWheelEvent(
        position, window.mapToGlobal(position), QPoint(), QPoint(0, 240),
        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
    )
    QGuiApplication.sendEvent(window, event)
    application.processEvents()

    assert math.isclose(document.workspace_state_2d.zoom, 1.15**2)
    assert viewport.cursorText == before
    assert window.findChild(QObject, "cursorCoordinates").property("text") == before


def test_double_click_and_reset_button_restore_the_view() -> None:
    application, document, view_model, engine, window = load_shell()
    view_model.workspace.setCamera2D(3.0, 4.0, 2.0)
    application.processEvents()

    QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, canvas_point(window, 50, 50))
    application.processEvents()
    assert document.workspace_state_2d == CameraState2D()

    view_model.workspace.setCamera2D(3.0, 4.0, 2.0)
    button = window.findChild(QObject, "resetViewButton")
    assert QMetaObject.invokeMethod(button, "click")
    application.processEvents()
    assert document.workspace_state_2d == CameraState2D()


def test_view_is_preserved_across_workspace_switches() -> None:
    application, document, view_model, engine, window = load_shell()
    viewport = view_model.viewport2D
    viewport.panBy(-150.0, 90.0)
    viewport.zoomAt(100.0, 100.0, 360.0)
    camera = document.workspace_state_2d
    origin = (viewport.originX, viewport.originY)

    view_model.workspace.setWorkspaceMode("3d")
    application.processEvents()
    assert window.findChild(QObject, "resetViewButton").property("visible") is False
    assert window.findChild(QObject, "camera2DSummary").property("visible") is False

    view_model.workspace.setWorkspaceMode("2d")
    application.processEvents()

    assert document.workspace_state_2d == camera
    assert (viewport.originX, viewport.originY) == origin
    assert window.findChild(QObject, "resetViewButton").property("visible") is True


def test_axes_hide_and_labels_stay_inside_when_origin_leaves_the_view() -> None:
    application, _, view_model, engine, window = load_shell()
    view_model.workspace.setCamera2D(50.0, 50.0, 1.0)
    application.processEvents()

    assert window.findChild(QObject, "xAxis").property("visible") is False
    assert window.findChild(QObject, "yAxis").property("visible") is False
    canvas = window.findChild(QQuickItem, "workspace2D")
    labels = window.findChild(QQuickItem, "labelLayer")
    for label in labels.childItems():
        if label.isVisible():
            assert 0 <= label.x() and label.x() + label.width() <= canvas.width()
            assert 0 <= label.y() and label.y() + label.height() <= canvas.height()


def create_canvas_item(source: str) -> tuple[QQmlApplicationEngine, QQmlComponent, QQuickItem]:
    """Create ``source`` next to the canvas2d components; callers keep all three alive."""
    create_gui_application(["pytest"])
    engine = QQmlApplicationEngine()
    component = QQmlComponent(engine)
    directory = QUrl.fromLocalFile(str(QML_DIRECTORY / "components" / "canvas2d") + "/")
    component.setData(source.encode(), directory.resolved(QUrl("Test.qml")))
    item = component.create()
    assert item is not None, component.errorString()
    return engine, component, item


def test_arrow_hides_when_zero_length_and_point_centres_itself() -> None:
    engine, component, root = create_canvas_item(
        """
        import QtQuick
        import "."
        Item {
            width: 200; height: 200
            Arrow2D { objectName: "zeroArrow"; x1: 10; y1: 10; x2: 10; y2: 10 }
            Arrow2D { objectName: "arrow"; x1: 10; y1: 10; x2: 110; y2: 10 }
            Segment2D { objectName: "segment"; x1: 0; y1: 0; x2: 50; y2: 50 }
            Point2D { objectName: "point"; centerX: 40; centerY: 60; radius2D: 5 }
        }
        """
    )

    assert root.findChild(QObject, "zeroArrow").property("visible") is False
    arrow = root.findChild(QObject, "arrow")
    assert arrow.property("visible") is True
    assert arrow.property("baseX") == 110 - arrow.property("headLength")
    point = root.findChild(QObject, "point")
    assert (point.property("x"), point.property("y")) == (35, 55)
    assert root.findChild(QObject, "segment") is not None
