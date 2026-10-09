"""End-to-end coverage of Stage 5: matrix editing, playback and both renderers."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow, QSGRendererInterface
from PySide6.QtTest import QTest

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.math_core import Matrix2, Vector2
from math_visualization.math_core.manim_port import smooth
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def find_item(item: QQuickItem, name: str) -> QQuickItem | None:
    """Search the visual item tree.

    Items a Repeater creates have no QObject parent, so ``findChild`` cannot
    reach them; they are only linked through ``parentItem``.
    """
    for child in item.childItems():
        if child.objectName() == name:
            return child
        found = find_item(child, name)
        if found is not None:
            return found
    return None


class Shell:
    def __init__(self, **view_model_options):
        self.application = create_gui_application(["pytest"])
        self.document = SceneDocument()
        self.app = ApplicationViewModel(self.document, **view_model_options)
        self.engine = QQmlApplicationEngine()
        assert load_main_qml(self.engine, self.app)
        self.window = self.engine.rootObjects()[0]
        self.window.requestActivate()
        QTest.qWaitForWindowActive(self.window, 1000)
        self.process()

    def process(self, rounds: int = 3) -> None:
        for _ in range(rounds):
            self.application.processEvents()

    def find(self, name: str) -> QObject:
        found = self.window.findChild(QObject, name) or find_item(self.window.contentItem(), name)
        assert found is not None, name
        return found

    def click(self, name: str) -> None:
        assert QMetaObject.invokeMethod(self.find(name), "click")
        self.process()

    def type_into(self, name: str, text: str) -> None:
        field = self.find(name)
        QMetaObject.invokeMethod(field, "forceActiveFocus")
        QMetaObject.invokeMethod(field, "selectAll")
        for character in text:
            for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                QGuiApplication.sendEvent(self.window, QKeyEvent(kind, Qt.Key_unknown, Qt.NoModifier, character))
        QTest.keyClick(self.window, Qt.Key_Return)
        self.process()

    def window_point(self, item_name: str, x: float, y: float) -> QPoint:
        return self.window.findChild(QQuickItem, item_name).mapToScene(QPointF(x, y)).toPoint()

    def rendered_pixel(self, item_name: str, x: float, y: float) -> QColor:
        image = QQuickWindow.grabWindow(self.window)
        ratio = image.width() / self.window.width()
        point = self.window.findChild(QQuickItem, item_name).mapToScene(QPointF(x, y))
        return image.pixelColor(round(point.x() * ratio), round(point.y() * ratio))

    def rhi_available(self) -> bool:
        interface = self.window.rendererInterface()
        return interface is not None and QSGRendererInterface.isApiRhiBased(interface.graphicsApi())


def close_to(actual: QColor, expected: str, tolerance: int = 60) -> bool:
    target = QColor(expected)
    return all(
        abs(a - b) <= tolerance
        for a, b in ((actual.red(), target.red()), (actual.green(), target.green()), (actual.blue(), target.blue()))
    )


def test_typing_entries_and_presets_edit_the_matrix_undoably() -> None:
    shell = Shell()

    for name, text in (("matrixEntryA", "2"), ("matrixEntryB", "1"), ("matrixEntryC", "-1"), ("matrixEntryD", "0.5")):
        shell.type_into(name, text)
    assert shell.document.matrix == Matrix2(2, 1, -1, 0.5)

    shell.click("preset_rotation")
    assert shell.document.matrix == Matrix2(0, -1, 1, 0)
    assert shell.find("matrixEntryB").property("text") == "-1"
    assert shell.app.scene.undo()
    assert shell.document.matrix == Matrix2(2, 1, -1, 0.5)


def test_invalid_entry_is_reported_and_reverts() -> None:
    shell = Shell()

    shell.type_into("matrixEntryC", "two")

    assert shell.document.matrix == Matrix2.identity()
    assert shell.find("matrixEntryC").property("text") == "0"
    assert "Matrix entry a₂₁" in shell.find("errorMessageLabel").property("text")


def test_play_runs_on_the_frame_clock_and_stops_at_the_end() -> None:
    shell = Shell()
    shell.click("preset_shear")
    shell.app.animation.setPlaybackSpeed(2.0)

    shell.click("playPauseButton")
    assert shell.app.animation.playing
    QTest.qWait(1600)
    shell.process()

    assert shell.app.animation.progress == 1.0
    assert shell.app.animation.playing is False
    assert shell.app.transformation.current_matrix() == Matrix2(1, 1, 0, 1)
    assert shell.find("animationProgressLabel").property("text") == "100%"


def test_scrubbing_pauses_and_reset_rewinds() -> None:
    shell = Shell()
    shell.click("preset_scale")
    shell.click("playPauseButton")

    slider = shell.window.findChild(QQuickItem, "animationProgressSlider")
    assert slider.height() >= 20  # a 0 px slider cannot be grabbed
    point = slider.mapToScene(QPointF(slider.width() * 0.5, slider.height() / 2)).toPoint()
    QTest.mouseClick(shell.window, Qt.LeftButton, Qt.NoModifier, point)
    shell.process()

    assert shell.app.animation.playing is False
    assert 0.4 < shell.app.animation.progress < 0.6
    shell.click("resetAnimationButton")
    assert shell.app.animation.progress == 0.0


def test_switching_views_at_forty_percent_keeps_progress_and_playback_continues() -> None:
    shell = Shell()
    identifier = shell.app.scene.addVector()
    shell.app.scene.setComponents(identifier, 2.0, 1.0)
    shell.click("preset_rotation")
    shell.app.animation.setProgress(0.4)

    shell.click("workspace3DTab")
    t = smooth(0.4)
    expected = Matrix2(1 - t, -t, t, 1 - t) @ Vector2(2, 1)
    assert shell.app.animation.progress == 0.4
    view = shell.app.viewport3D.viewport()
    label = shell.app.viewport3D.vectorLabels[0]
    tip = view.project((expected.x, expected.y, 0.0))
    assert (label["x"], label["y"]) == pytest.approx((tip.x, tip.y))

    shell.app.animation.setPlaybackSpeed(2.0)
    shell.click("playPauseButton")
    QTest.qWait(1300)
    shell.process()
    assert shell.app.animation.progress == 1.0

    shell.click("workspace2DTab")
    shape = shell.app.viewport2D.vectorShapes[0]
    origin = (shell.app.viewport2D.originX, shell.app.viewport2D.originY)
    assert (shape["tipX"] - origin[0], origin[1] - shape["tipY"]) == pytest.approx((-80.0, 160.0))


def test_visual_toggles_hide_layers_in_both_views() -> None:
    shell = Shell()

    shell.click("toggle_show_unit_square")
    shell.click("toggle_show_transformed_grid")

    assert shell.document.visual_state.show_unit_square is False
    assert shell.find("unitSquare").property("visible") is False
    assert shell.find("transformedGrid").property("visible") is False
    shell.click("workspace3DTab")
    assert shell.find("unitSquare3D").property("visible") is False
    assert shell.find("transformedGrid3D").property("visible") is False


def test_expression_panel_describes_the_transformation() -> None:
    shell = Shell()
    shell.app.scene.addVector()
    shell.click("preset_shear")
    shell.app.animation.setProgress(1.0)
    shell.process()

    assert shell.find("targetMatrixText").property("text") == "A = [ 1  1 ; 0  1 ]"
    assert shell.find("currentMatrixText").property("text").endswith("[ 1  1 ; 0  1 ]")
    assert shell.find("selectedMappingText").property("text") == "A(t)·u = A(t)·(1, 1) = (2, 1)"


def test_dragging_the_ghost_edits_the_input_while_transformed() -> None:
    shell = Shell()
    identifier = shell.app.scene.addVector()
    shell.app.scene.setComponents(identifier, 1.0, 0.0)
    shell.click("preset_scale")
    shell.app.animation.setProgress(1.0)
    shell.process()
    shape = shell.app.viewport2D.vectorShapes[0]

    start = shell.window_point("viewportPointerArea", shape["ghostX"], shape["ghostY"])
    end = start + QPoint(0, -80)
    QTest.mousePress(shell.window, Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(shell.window, start + QPoint(0, -40))
    QTest.mouseMove(shell.window, end)
    QTest.mouseRelease(shell.window, Qt.LeftButton, Qt.NoModifier, end)
    shell.process()

    assert shell.document.vectors[0].vector == Vector2(1, 1)
    assert shell.app.transformation.selectedMappingText.endswith("= (2, 0.5)")


def test_rendered_2d_basis_and_unit_square_follow_the_matrix() -> None:
    shell = Shell()
    shell.click("preset_shear")
    shell.app.animation.setProgress(1.0)
    shell.process(10)
    viewport = shell.app.viewport2D
    origin = (viewport.originX, viewport.originY)

    def screen(x, y):
        return origin[0] + x * 80.0, origin[1] - y * 80.0

    # ĵ = A·e₂ = (1, 1) is red; the sheared square covers (1.7, 0.9) in yellow
    # (clear of the det label at its centre, A·(0.5, 0.5) = (1, 0.5)).
    assert close_to(shell.rendered_pixel("workspace2D", *screen(0.5, 0.5)), "#FC6255")
    assert close_to(shell.rendered_pixel("workspace2D", *screen(0.55, 0.0)), "#83C167")
    square = shell.rendered_pixel("workspace2D", *screen(1.7, 0.9))
    assert square.red() > 70 and square.green() > 70 and square.blue() < square.red() - 30


def test_rendered_3d_basis_vectors_match_python_geometry() -> None:
    shell = Shell()
    if not shell.rhi_available():
        pytest.skip("Qt Quick 3D needs an RHI-based graphics API")
    shell.click("preset_shear")
    shell.app.animation.setProgress(1.0)
    shell.click("workspace3DTab")
    shell.app.viewport3D.applyPreset("top")
    shell.process(10)
    view = shell.app.viewport3D.viewport()

    j_mid = view.project((0.45, 0.45, 0.0))
    i_mid = view.project((0.5, 0.0, 0.0))
    assert close_to(shell.rendered_pixel("workspace3D", j_mid.x, j_mid.y), "#FC6255")
    assert close_to(shell.rendered_pixel("workspace3D", i_mid.x, i_mid.y), "#83C167")
