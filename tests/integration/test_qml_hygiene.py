"""The QML shell must load with the intended style and without any warnings."""

from __future__ import annotations

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import math_visualization.application as application_module
from math_visualization.application import (
    QUICK_CONTROLS_STYLE,
    configure_controls_style,
    create_gui_application,
    load_main_qml,
)
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


# Emitted only where Qt Quick 3D has no GPU API (the offscreen test platform).
ENVIRONMENT_MESSAGES = ("Qt Quick 3D is not functional", "isApiRhiBased")


def test_fusion_style_is_used_so_the_palette_applies() -> None:
    create_gui_application(["pytest"])
    engine = QQmlApplicationEngine()
    view_model = ApplicationViewModel(SceneDocument())

    assert load_main_qml(engine, view_model)
    assert QQuickStyle.name() == QUICK_CONTROLS_STYLE == "Fusion"


def test_environment_variable_overrides_the_style(monkeypatch) -> None:
    requested: list[str] = []
    monkeypatch.setattr(application_module.QQuickStyle, "setStyle", requested.append)

    monkeypatch.setattr(application_module, "_style_configured", False)
    monkeypatch.setenv("QT_QUICK_CONTROLS_STYLE", "Material")
    configure_controls_style()
    assert requested == []

    monkeypatch.setattr(application_module, "_style_configured", False)
    monkeypatch.delenv("QT_QUICK_CONTROLS_STYLE")
    configure_controls_style()
    configure_controls_style()
    assert requested == ["Fusion"]


def test_shell_runs_without_qml_warnings() -> None:
    application = create_gui_application(["pytest"])
    messages: list[str] = []

    def handler(kind, context, message):
        if kind != QtMsgType.QtDebugMsg and not any(text in message for text in ENVIRONMENT_MESSAGES):
            messages.append(message)

    previous = qInstallMessageHandler(handler)
    try:
        engine = QQmlApplicationEngine()
        view_model = ApplicationViewModel(SceneDocument())
        assert load_main_qml(engine, view_model)
        view_model.scene.addVector()
        for mode in ("3d", "2d"):
            view_model.workspace.setWorkspaceMode(mode)
            application.processEvents()
        view_model.toggleThemeMode()
        application.processEvents()
        del engine
    finally:
        qInstallMessageHandler(previous)

    assert messages == []


def _button_text_contrast(window, button) -> float:
    """Largest colour distance between the button's face and any pixel on it."""
    from PySide6.QtCore import QPointF
    from PySide6.QtQuick import QQuickWindow

    image = QQuickWindow.grabWindow(window)
    ratio = image.width() / window.width()
    top_left = button.mapToScene(QPointF(0, 0))
    left, top = round(top_left.x() * ratio), round(top_left.y() * ratio)
    width, height = round(button.width() * ratio), round(button.height() * ratio)
    face = image.pixelColor(left + 3, top + height // 2)
    contrast = 0.0
    for x in range(left + 2, left + width - 2):
        for y in range(top + 2, top + height - 2):
            pixel = image.pixelColor(x, y)
            contrast = max(
                contrast,
                abs(pixel.red() - face.red()) + abs(pixel.green() - face.green()) + abs(pixel.blue() - face.blue()),
            )
    return contrast


def test_disabled_buttons_are_visibly_dimmed_from_startup_in_both_themes() -> None:
    from PySide6.QtQuick import QQuickItem

    application = create_gui_application(["pytest"])
    engine = QQmlApplicationEngine()
    view_model = ApplicationViewModel(SceneDocument())
    assert load_main_qml(engine, view_model)
    window = engine.rootObjects()[0]
    button = window.findChild(QQuickItem, "deleteVectorButton")

    def settle():
        for _ in range(5):
            application.processEvents()

    for theme in ("dark", "light"):
        view_model.setThemeMode(theme)
        view_model.scene.clearSelection()
        settle()
        assert button.isEnabled() is False
        disabled = _button_text_contrast(window, button)
        view_model.scene.addVector()
        settle()
        enabled = _button_text_contrast(window, button)
        assert disabled < enabled * 0.7, (theme, disabled, enabled)
        view_model.scene.removeSelected()
    del engine
