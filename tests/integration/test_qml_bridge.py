"""Offscreen integration coverage for the Stage 0 Python/QML bridge."""

from __future__ import annotations

import logging

from PySide6.QtCore import QMetaObject, QObject
from PySide6.QtQml import QQmlApplicationEngine

from math_visualization.application import create_gui_application, load_main_qml
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def test_qml_reads_property_calls_slot_and_receives_signal() -> None:
    application = create_gui_application(["pytest"])
    view_model = ApplicationViewModel(SceneDocument())
    engine = QQmlApplicationEngine()

    assert load_main_qml(engine, view_model)
    root = engine.rootObjects()[0]
    status_label = root.findChild(QObject, "statusLabel")
    assert status_label is not None
    assert status_label.property("text") == "Status: Ready"

    assert QMetaObject.invokeMethod(root, "testPythonConnection")
    application.processEvents()

    assert view_model.statusMessage == "Python connection OK"
    assert status_label.property("text") == "Status: Python connection OK"


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
