"""Offscreen integration coverage for the Stage 0 Python/QML bridge."""

from __future__ import annotations

import logging

from PySide6.QtCore import QMetaObject, QObject
from PySide6.QtQml import QQmlApplicationEngine

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def load_qml_root():
    """Load the application shell with a live Stage 0 view model."""
    application = create_gui_application(["pytest"])
    view_model = ApplicationViewModel(SceneDocument())
    engine = QQmlApplicationEngine()

    assert load_main_qml(engine, view_model)
    return application, view_model, engine, engine.rootObjects()[0]


def test_qml_reads_property_calls_slot_and_receives_signal() -> None:
    application, view_model, engine, root = load_qml_root()
    status_label = root.findChild(QObject, "statusLabel")
    assert status_label is not None
    assert status_label.property("text") == "Status: Ready"

    assert QMetaObject.invokeMethod(root, "testPythonConnection")
    application.processEvents()

    assert view_model.statusMessage == "Python connection OK"
    assert status_label.property("text") == "Status: Python connection OK"


def test_qml_shell_contains_structural_regions_and_toggleable_dock() -> None:
    application, _, engine, root = load_qml_root()
    expected_regions = (
        "mainArea",
        "leftPanel",
        "centerArea",
        "visualizationArea",
        "rightPanel",
        "expressionDock",
        "animationBar",
        "statusBar",
        "workspace2D",
    )

    for object_name in expected_regions:
        assert root.findChild(QObject, object_name) is not None

    assert root.findChild(QObject, "topBar") is None

    expression_dock = root.findChild(QObject, "expressionDock")
    assert expression_dock.property("expanded") is True
    assert QMetaObject.invokeMethod(root, "toggleExpressionDock")
    application.processEvents()
    assert expression_dock.property("expanded") is False

    assert QMetaObject.invokeMethod(root, "toggleExpressionDock")
    application.processEvents()
    assert expression_dock.property("expanded") is True

    workspace_3d_tab = root.findChild(QObject, "workspace3DTab")
    assert workspace_3d_tab is not None
    assert QMetaObject.invokeMethod(workspace_3d_tab, "click")
    application.processEvents()
    assert root.findChild(QObject, "workspace3D") is not None


def test_missing_qml_entry_returns_failure(tmp_path) -> None:
    create_gui_application(["pytest"])
    engine = QQmlApplicationEngine()
    view_model = ApplicationViewModel(SceneDocument())

    assert not load_main_qml(engine, view_model, tmp_path / "missing.qml")


def test_invalid_qml_entry_returns_failure(tmp_path) -> None:
    create_gui_application(["pytest"])
    invalid_qml = tmp_path / "invalid.qml"
    invalid_qml.write_text("not valid qml", encoding="utf-8")
    engine = QQmlApplicationEngine()
    view_model = ApplicationViewModel(SceneDocument())

    assert not load_main_qml(
        engine,
        view_model,
        invalid_qml,
        logger=logging.getLogger("test.invalid_qml"),
    )
