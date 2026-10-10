"""End-to-end coverage of Stage 7: menus, shortcuts, saving, the unsaved-changes guard and recovery."""

from __future__ import annotations

import json

from PySide6.QtCore import QMetaObject, QObject, Q_ARG, QUrl, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from test_transformation_ui import Shell

from math_visualization.math_core import Matrix2
from math_visualization.persistence import RecentProjects, RecoveryStore
from math_visualization.scene.scene_document import SceneDocument


def call(shell: Shell, function: str, *arguments: str) -> None:
    QMetaObject.invokeMethod(shell.window, function, *(Q_ARG("QVariant", argument) for argument in arguments))
    shell.process(5)


def dialog(shell: Shell) -> QObject:
    return shell.window.findChild(QObject, "unsavedChangesDialog")


def press_dialog_button(shell: Shell, text: str) -> None:
    """Click a visible button of the unsaved-changes dialog by its label."""

    def search(item: QQuickItem):
        for child in item.childItems():
            if child.property("text") == text and child.isVisible() and child.metaObject().indexOfMethod("click()") >= 0:
                return child
            found = search(child)
            if found is not None:
                return found
        return None

    button = search(dialog(shell).property("footer"))
    assert button is not None, text
    QMetaObject.invokeMethod(button, "click")
    shell.process(5)


def test_title_marks_unsaved_changes_and_names_the_file(tmp_path) -> None:
    shell = Shell()
    assert shell.window.title() == "Untitled — Math Visualization"

    shell.app.scene.addVector()
    shell.process()
    assert shell.window.title() == "Untitled* — Math Visualization"

    call(shell, "finishSaveAs", QUrl.fromLocalFile(str(tmp_path / "lesson")).toString(), "")
    assert shell.window.title() == "lesson — Math Visualization"
    assert json.loads((tmp_path / "lesson.mvscene").read_text(encoding="utf-8"))["vectors"][0]["name"] == "u"


def test_undo_and_redo_shortcuts_and_menu_texts() -> None:
    shell = Shell()
    shell.app.scene.addVector()
    shell.click("preset_rotation")
    undo = shell.find("undoAction")
    assert undo.property("text") == "Undo Edit A" and undo.property("enabled")

    QTest.keyClick(shell.window, Qt.Key_Z, Qt.ControlModifier)
    shell.process()
    assert shell.document.matrix == Matrix2.identity()
    assert shell.find("redoAction").property("text") == "Redo Edit A"

    QTest.keyClick(shell.window, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    shell.process()
    assert shell.document.matrix == Matrix2(0, -1, 1, 0)


def test_ctrl_z_in_a_text_field_undoes_typing_not_the_document() -> None:
    shell = Shell()
    shell.app.scene.addVector()
    field = shell.find("matrixEntryA")
    QMetaObject.invokeMethod(field, "forceActiveFocus")
    QTest.keyClick(shell.window, Qt.Key_End)
    QTest.keyClick(shell.window, Qt.Key_5)
    shell.process()

    QTest.keyClick(shell.window, Qt.Key_Z, Qt.ControlModifier)
    shell.process()
    assert len(shell.document.vectors) == 1


def test_closing_with_unsaved_changes_asks_first() -> None:
    shell = Shell()
    shell.app.scene.addVector()
    shell.process()

    shell.window.close()
    shell.process(5)
    assert shell.window.isVisible()
    assert dialog(shell).property("visible")

    press_dialog_button(shell, "Cancel")
    assert shell.window.isVisible() and not dialog(shell).property("visible")

    shell.window.close()
    shell.process(5)
    press_dialog_button(shell, "Discard")
    assert not shell.window.isVisible()


def test_closing_a_saved_project_does_not_ask(tmp_path) -> None:
    shell = Shell()
    shell.app.scene.addVector()
    call(shell, "finishSaveAs", str(tmp_path / "done.mvscene"), "")

    shell.window.close()
    shell.process(5)
    assert not shell.window.isVisible()


def test_new_with_unsaved_changes_can_save_first(tmp_path) -> None:
    shell = Shell()
    shell.app.scene.addVector()
    call(shell, "finishSaveAs", str(tmp_path / "keep.mvscene"), "")
    shell.click("preset_shear")

    call(shell, "guard", "new")
    assert dialog(shell).property("visible")
    press_dialog_button(shell, "Save")

    assert shell.document.vectors == [] and shell.app.project.displayName == "Untitled"
    saved = json.loads((tmp_path / "keep.mvscene").read_text(encoding="utf-8"))
    assert saved["matrices"][0]["entries"] == [[1.0, 1.0], [0.0, 1.0]]


def test_open_recent_reopens_through_the_guard(tmp_path) -> None:
    shell = Shell(recent=RecentProjects())
    shell.app.scene.addVector()
    call(shell, "finishSaveAs", str(tmp_path / "first.mvscene"), "")
    call(shell, "guard", "new")
    assert shell.find("recentMenu").property("enabled")

    call(shell, "guard", "recent:" + str(tmp_path / "first.mvscene"))
    assert [vector.name for vector in shell.document.vectors] == ["u"]
    assert shell.app.project.displayName == "first"


def test_damaged_file_shows_an_error_banner(tmp_path) -> None:
    shell = Shell()
    broken = tmp_path / "broken.mvscene"
    broken.write_text('{"format": "math-visualization-scene", "schema_version": 1}', encoding="utf-8")

    call(shell, "guard", "recent:" + str(broken))
    assert shell.find("errorBanner").property("visible")
    assert "broken.mvscene is damaged" in shell.find("errorMessageLabel").property("text")


def test_recovery_banner_restores_the_previous_session(tmp_path) -> None:
    snapshot = SceneDocument()
    snapshot.matrix = Matrix2(2, 0, 0, 2)
    RecoveryStore(tmp_path).write(snapshot, None)
    shell = Shell(recovery=RecoveryStore(tmp_path))
    assert shell.find("recoveryBanner").property("visible")

    shell.click("restoreRecoveryButton")
    assert shell.document.matrix == Matrix2(2, 0, 0, 2)
    assert not shell.find("recoveryBanner").property("visible")
    assert shell.window.title() == "Untitled* — Math Visualization"
