"""Offscreen integration coverage for Stage 1 workspace state in the QML shell."""

from __future__ import annotations

from PySide6.QtCore import QMetaObject, QObject
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def load_shell():
    application = create_gui_application(["pytest"])
    document = SceneDocument()
    view_model = ApplicationViewModel(document)
    engine = QQmlApplicationEngine()
    assert load_main_qml(engine, view_model)
    return application, document, view_model, engine, engine.rootObjects()[0]


def loaded_workspace(root: QObject) -> str:
    return root.findChild(QObject, "workspaceLoader").property("item").objectName()


def click(root: QObject, object_name: str, application) -> None:
    target = root.findChild(QObject, object_name)
    assert target is not None, object_name
    assert QMetaObject.invokeMethod(target, "click")
    application.processEvents()


def test_workspace_tabs_drive_python_state_without_rebuilding_document() -> None:
    application, document, view_model, engine, root = load_shell()

    click(root, "workspace3DTab", application)

    assert view_model.workspace.workspaceMode == "3d"
    assert view_model.document is document
    assert loaded_workspace(root) == "workspace3D"

    view_model.workspace.setWorkspaceMode("2d")
    application.processEvents()

    assert root.findChild(QObject, "workspaceTabs").property("currentIndex") == 0
    assert loaded_workspace(root) == "workspace2D"


def test_workspace_cameras_and_progress_survive_switching() -> None:
    application, _, view_model, engine, root = load_shell()
    view_model.workspace.setCamera2D(1.0, -2.0, 1.5)
    view_model.workspace.setCamera3D(0.0, 0.0, 0.0, 120.0, 15.0, 8.0)
    view_model.animation.setProgress(0.4)
    application.processEvents()

    click(root, "workspace3DTab", application)
    summary_3d = root.findChild(QObject, "camera3DSummary").property("text")
    click(root, "workspace2DTab", application)
    summary_2d = root.findChild(QObject, "camera2DSummary").property("text")

    assert "azimuth 120.0" in summary_3d
    assert "distance 8.00" in summary_3d
    assert summary_2d == "Camera: center (1.00, -2.00), zoom 1.50"
    assert view_model.animation.progress == 0.4
    assert root.findChild(QObject, "animationProgressLabel").property("text") == "40%"
    assert root.findChild(QObject, "animationProgressSlider").property("value") == 0.4


def test_theme_toggle_switches_palette() -> None:
    application, _, view_model, engine, root = load_shell()
    dark_background = QColor(root.property("color"))

    click(root, "themeToggleButton", application)

    assert view_model.themeMode == "light"
    assert QColor(root.property("color")) != dark_background

    view_model.setThemeMode("dark")
    application.processEvents()
    assert QColor(root.property("color")) == dark_background


def test_errors_are_shown_and_dismissible() -> None:
    application, _, view_model, engine, root = load_shell()
    banner = root.findChild(QObject, "errorBanner")
    assert banner.property("visible") is False

    view_model.workspace.setWorkspaceMode("4d")
    application.processEvents()

    assert banner.property("visible") is True
    assert "4d" in root.findChild(QObject, "errorMessageLabel").property("text")

    click(root, "errorDismissButton", application)

    assert view_model.errorMessage == ""
    assert banner.property("visible") is False


def test_layout_respects_minimum_window_size() -> None:
    application, _, _, engine, root = load_shell()
    root.setProperty("width", root.property("minimumWidth"))
    root.setProperty("height", root.property("minimumHeight"))
    application.processEvents()

    window_width = root.property("width")
    for object_name in ("leftPanel", "centerArea", "rightPanel"):
        region = root.findChild(QObject, object_name)
        assert region.property("width") > 0, object_name
        assert region.property("x") + region.property("width") <= window_width + 1, object_name

    visualization = root.findChild(QObject, "visualizationArea")
    assert visualization.property("height") >= 260
