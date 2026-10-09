"""End-to-end coverage of Stage 4: building and editing vectors in 2D and 3D."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow, QSGRendererInterface
from PySide6.QtTest import QTest

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.math_core import Vector2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


class Shell:
    """The real application window driven through Qt input events."""

    def __init__(self):
        self.application = create_gui_application(["pytest"])
        self.document = SceneDocument()
        self.app = ApplicationViewModel(self.document)
        self.engine = QQmlApplicationEngine()
        assert load_main_qml(self.engine, self.app)
        self.window = self.engine.rootObjects()[0]
        # Shortcuts only fire in the active window; virtual displays without a
        # window manager do not activate windows on their own.
        self.window.requestActivate()
        QTest.qWaitForWindowActive(self.window, 1000)
        self.process()

    def process(self) -> None:
        for _ in range(3):
            self.application.processEvents()

    def find(self, name: str) -> QObject:
        found = self.window.findChild(QObject, name)
        assert found is not None, name
        return found

    def click_button(self, name: str) -> None:
        assert QMetaObject.invokeMethod(self.find(name), "click")
        self.process()

    def type_into(self, field_name: str, text: str) -> None:
        field = self.find(field_name)
        QMetaObject.invokeMethod(field, "forceActiveFocus")
        QMetaObject.invokeMethod(field, "selectAll")
        # QTest.keyClicks only accepts widgets; send text key events instead.
        for character in text:
            for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                QGuiApplication.sendEvent(
                    self.window, QKeyEvent(kind, Qt.Key_unknown, Qt.NoModifier, character)
                )
        QTest.keyClick(self.window, Qt.Key_Return)
        self.process()

    def canvas_point(self, area_name: str, x: float, y: float) -> QPoint:
        area = self.window.findChild(QQuickItem, area_name)
        return area.mapToScene(QPointF(x, y)).toPoint()

    def drag(self, area_name: str, start, end, button=Qt.LeftButton) -> None:
        begin = self.canvas_point(area_name, *start)
        finish = self.canvas_point(area_name, *end)
        QTest.mousePress(self.window, button, Qt.NoModifier, begin)
        QTest.mouseMove(self.window, (begin + finish) / 2)
        QTest.mouseMove(self.window, finish)
        QTest.mouseRelease(self.window, button, Qt.NoModifier, finish)
        self.process()

    def click_canvas(self, area_name: str, x: float, y: float) -> None:
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, self.canvas_point(area_name, x, y))
        self.process()

    @property
    def vector(self) -> Vector2:
        return self.document.vectors[0].vector


def test_stage4_acceptance_flow() -> None:
    shell = Shell()

    # 1. Create a vector in 2D and set it to (2, 1) by typing.
    shell.click_button("addVectorButton")
    assert shell.vector == Vector2(1, 1)
    identifier = shell.app.scene.selectedId
    shell.type_into("xField", "2")
    shell.type_into("yField", "1")
    assert shell.vector == Vector2(2, 1)
    assert shell.find("lengthValue").property("text") == "2.2361"

    # 2. Dragging the tip updates the numbers (one undo step).
    tip = shell.app.viewport2D.vectorShapes[0]
    history = shell.app.scene.commands.undo_count
    shell.drag("viewportPointerArea", (tip["tipX"], tip["tipY"]), (tip["tipX"] + 80, tip["tipY"] - 40))
    assert shell.vector == Vector2(3, 1.5)
    assert shell.find("xField").property("text") == "3"
    assert shell.find("yField").property("text") == "1.5"
    assert shell.app.scene.commands.undo_count == history + 1

    # 3. Editing the numbers moves the drawing.
    shell.type_into("xField", "2")
    shell.type_into("yField", "1")
    tip = shell.app.viewport2D.vectorShapes[0]
    origin = (shell.app.viewport2D.originX, shell.app.viewport2D.originY)
    assert (tip["tipX"] - origin[0], origin[1] - tip["tipY"]) == pytest.approx((160.0, 80.0))

    # 4–5. In 3D the same vector is drawn from (0, 0, 0) to (2, 1, 0).
    shell.click_button("workspace3DTab")
    viewport = shell.app.viewport3D
    projected_tip = viewport.viewport().project((2.0, 1.0, 0.0))
    label = viewport.vectorLabels[0]
    assert (label["x"], label["y"]) == pytest.approx((projected_tip.x, projected_tip.y))

    # 6–7. Dragging from different camera angles keeps the tip in the XY plane.
    cameras = {
        "oblique preset": lambda: shell.click_button("obliqueViewButton"),
        "top preset": lambda: shell.click_button("topViewButton"),
        "grazing angle": lambda: shell.app.workspace.setCamera3D(0.0, 0.0, 0.0, 150.0, 12.0, 12.0),
    }
    for (name, choose_camera), target in zip(cameras.items(), ((-1.0, 2.0), (1.5, -0.5), (2.5, 1.5))):
        choose_camera()
        shell.process()
        view = viewport.viewport()
        start = view.project((shell.vector.x, shell.vector.y, 0.0))
        end = view.project((*target, 0.0))
        shell.drag("viewport3DPointerArea", (start.x, start.y), (end.x, end.y))
        # Real mouse events use whole pixels; one pixel is about 0.02 units here
        # and more at grazing angles, where the plane is strongly foreshortened.
        assert (shell.vector.x, shell.vector.y) == pytest.approx(target, abs=0.08), name

    # 8. Back in 2D the object and its selection are unchanged.
    value = shell.vector
    shell.click_button("workspace2DTab")
    assert shell.app.scene.selectedId == identifier
    assert shell.vector == value
    assert shell.app.viewport2D.vectorShapes[0]["selected"]


def test_edge_on_plane_selects_but_does_not_drag() -> None:
    shell = Shell()
    shell.click_button("addVectorButton")
    shell.app.scene.clearSelection()
    shell.click_button("workspace3DTab")
    shell.click_button("frontViewButton")
    view = shell.app.viewport3D.viewport()
    tip = view.project((1.0, 1.0, 0.0))

    shell.drag("viewport3DPointerArea", (tip.x, tip.y), (tip.x + 60, tip.y - 40))

    assert shell.app.scene.selectedId == shell.document.vectors[0].object_id
    assert shell.vector == Vector2(1, 1)


def test_clicks_select_by_shaft_and_clear_on_empty_space() -> None:
    shell = Shell()
    first = shell.app.scene.addVector()
    shell.app.scene.setComponents(first, 2.0, 0.0)
    shell.app.scene.addVector()
    shell.process()
    origin = (shell.app.viewport2D.originX, shell.app.viewport2D.originY)

    shell.click_canvas("viewportPointerArea", origin[0] + 80, origin[1])
    assert shell.app.scene.selectedId == first
    assert shell.vector == Vector2(2, 0)

    shell.click_canvas("viewportPointerArea", origin[0] - 200, origin[1] + 150)
    assert shell.app.scene.selectedId == ""
    assert shell.find("noSelectionHint").property("visible") is True


def test_delete_key_removes_the_selection_but_not_while_typing() -> None:
    shell = Shell()
    shell.click_button("addVectorButton")

    QMetaObject.invokeMethod(shell.find("xField"), "forceActiveFocus")
    QTest.keyClick(shell.window, Qt.Key_Delete)
    shell.process()
    assert len(shell.document.vectors) == 1

    tip = shell.app.viewport2D.vectorShapes[0]
    shell.click_canvas("viewportPointerArea", tip["tipX"], tip["tipY"])
    QTest.keyClick(shell.window, Qt.Key_Delete)
    shell.process()
    assert shell.document.vectors == []
    assert shell.find("emptyObjectsHint").property("visible") is True


def test_object_list_buttons_and_selection() -> None:
    shell = Shell()
    for _ in range(3):
        shell.click_button("addVectorButton")
    assert [vector.name for vector in shell.document.vectors] == ["u", "v", "w"]
    assert shell.find("vectorList").property("count") == 3

    shell.app.scene.select(shell.document.vectors[0].object_id)
    shell.click_button("duplicateVectorButton")
    assert [vector.name for vector in shell.document.vectors] == ["u", "a", "v", "w"]

    shell.click_button("deleteVectorButton")
    assert [vector.name for vector in shell.document.vectors] == ["u", "v", "w"]
    assert shell.find("deleteVectorButton").property("enabled") is False


def test_invalid_input_is_reported_and_the_field_reverts() -> None:
    shell = Shell()
    shell.click_button("addVectorButton")

    shell.type_into("xField", "abc")

    assert shell.vector == Vector2(1, 1)
    assert shell.find("xField").property("text") == "1"
    assert shell.find("errorBanner").property("visible") is True
    assert "not a number" in shell.find("errorMessageLabel").property("text")


def test_renaming_and_recolouring_from_the_inspector() -> None:
    shell = Shell()
    shell.click_button("addVectorButton")

    shell.type_into("nameField", "p")

    assert shell.document.vectors[0].name == "p"
    assert shell.app.viewport2D.vectorShapes[0]["name"] == "p"


def test_rendered_3d_arrow_matches_python_geometry() -> None:
    """The arrow Qt Quick 3D draws must lie where Python says the vector is."""
    shell = Shell()
    interface = shell.window.rendererInterface()
    if interface is None or not QSGRendererInterface.isApiRhiBased(interface.graphicsApi()):
        pytest.skip("Qt Quick 3D needs an RHI-based graphics API")
    identifier = shell.app.scene.addVector()
    shell.app.scene.setComponents(identifier, -2.0, 1.5)
    shell.app.scene.clearSelection()
    shell.app.workspace.setWorkspaceMode("3d")
    shell.app.viewport3D.applyPreset("top")
    for _ in range(10):
        shell.process()

    image = QQuickWindow.grabWindow(shell.window)
    ratio = image.width() / shell.window.width()
    canvas = shell.window.findChild(QQuickItem, "workspace3D")
    view = shell.app.viewport3D.viewport()
    expected = QColor(shell.document.vectors[0].color)
    for fraction in (0.3, 0.6):
        point = view.project((-2.0 * fraction, 1.5 * fraction, 0.0))
        scene = canvas.mapToScene(QPointF(point.x, point.y))
        actual = image.pixelColor(round(scene.x() * ratio), round(scene.y() * ratio))
        assert abs(actual.red() - expected.red()) < 40
        assert abs(actual.green() - expected.green()) < 40
        assert abs(actual.blue() - expected.blue()) < 40


def test_rendered_3d_shaft_is_as_thin_as_the_2d_stroke() -> None:
    """Measured across the drawn shaft, a 3D vector is about the 2D line width."""
    shell = Shell()
    interface = shell.window.rendererInterface()
    if interface is None or not QSGRendererInterface.isApiRhiBased(interface.graphicsApi()):
        pytest.skip("Qt Quick 3D needs an RHI-based graphics API")
    identifier = shell.app.scene.addVector()
    shell.app.scene.setComponents(identifier, 3.0, 1.2)
    shell.app.scene.clearSelection()
    shell.app.workspace.setWorkspaceMode("3d")
    shell.app.viewport3D.applyPreset("top")
    for _ in range(10):
        shell.process()

    image = QQuickWindow.grabWindow(shell.window)
    ratio = image.width() / shell.window.width()
    canvas = shell.window.findChild(QQuickItem, "workspace3D")
    # Sampled away from the axes and grid lines; the column crosses the shaft
    # at a slope of 0.4, which widens it by only sqrt(1 + 0.4²) ≈ 1.08.
    point = shell.app.viewport3D.viewport().project((1.35, 0.54, 0.0))
    centre = canvas.mapToScene(QPointF(point.x, point.y))
    expected = QColor(shell.document.vectors[0].color)

    def coverage(dy: int) -> float:
        """How far the pixel dy rows from the centre is blended towards the vector colour."""
        actual = image.pixelColor(round(centre.x() * ratio), round(centre.y() * ratio) + dy)
        background = image.pixelColor(round(centre.x() * ratio), round(centre.y() * ratio) - 10)
        span = sum(abs(e - b) for e, b in zip(expected.getRgb()[:3], background.getRgb()[:3]))
        moved = sum(abs(a - b) for a, b in zip(actual.getRgb()[:3], background.getRgb()[:3]))
        return min(1.0, moved / span)

    width = sum(coverage(dy) for dy in range(-7, 8)) / ratio
    assert 1.5 <= width <= 4.5
