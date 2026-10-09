"""Tests for the project view model: save / open / new, dirty state, history and recovery."""

from pathlib import Path

from PySide6.QtCore import QUrl

from math_visualization.math_core import Matrix2
from math_visualization.persistence import RecentProjects, RecoveryStore
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel


def make_app(recovery_dir=None, recent=None):
    document = SceneDocument()
    app = ApplicationViewModel(
        document, recent=recent, recovery=RecoveryStore(recovery_dir) if recovery_dir else None
    )
    app.viewport2D.setViewportSize(800.0, 600.0)
    app.viewport3D.setViewportSize(900.0, 600.0)
    return document, app


def build_scene(app) -> None:
    first = app.scene.addVector()
    app.scene.setComponents(first, 2.0, -1.0)
    app.scene.addVector()
    app.scene.select(first)
    app.transformation.applyPreset("shear")
    app.animation.setProgress(0.4)
    app.animation.setRateFunction("linear")
    app.transformation.setVisualFlag("show_kernel", False)
    app.workspace.setWorkspaceMode("3d")
    app.viewport3D.orbitBy(40.0, -20.0)
    app.viewport3D.toggleProjectionMode()
    app.viewport2D.zoomAt(400.0, 300.0, 240.0)


def test_save_then_open_restores_objects_cameras_animation_and_options(tmp_path) -> None:
    document, app = make_app()
    build_scene(app)
    path = tmp_path / "demo.mvscene"

    assert app.project.saveProjectAs(str(path))
    assert not app.project.dirty and document.title == "demo"
    expected = SceneDocument()
    expected.replace_contents(document)

    app.project.newProject()
    assert document.vectors == [] and document.matrix == Matrix2.identity()
    assert app.project.displayName == "Untitled"

    assert app.project.openProject(str(path))
    assert document == expected
    # Every view model shows the reopened state.
    assert app.scene.vectorModel.rowCount() == 2
    assert app.transformation.entryTexts == ["1", "1", "0", "1"]
    assert app.animation.progress == 0.4 and app.animation.rateFunction == "linear"
    assert app.workspace.workspaceMode == "3d"
    assert app.viewport3D.projectionMode == "orthographic"
    assert app.inspector.xText == "2"
    assert not app.transformation.visualState["show_kernel"]
    assert app.project.displayName == "demo" and not app.project.dirty
    assert not app.project.canUndo


def test_open_accepts_file_urls_and_save_as_adds_the_extension(tmp_path) -> None:
    _, app = make_app()
    app.scene.addVector()

    assert app.project.saveProjectAs(str(tmp_path / "plain"))
    assert app.project.filePath == str(tmp_path / "plain.mvscene")
    assert app.project.openProject(QUrl.fromLocalFile(str(tmp_path / "plain.mvscene")).toString())


def test_dirty_follows_edits_and_saved_settings_not_the_view(tmp_path) -> None:
    _, app = make_app()
    project = app.project
    assert not project.dirty and project.windowTitle == "Untitled — Math Visualization"

    identifier = app.scene.addVector()
    assert project.dirty and project.windowTitle == "Untitled* — Math Visualization"
    app.scene.undo()
    assert not project.dirty

    app.transformation.setVisualFlag("show_ghosts", False)
    assert project.dirty
    app.transformation.setVisualFlag("show_ghosts", True)
    assert not project.dirty

    app.animation.setPlaybackSpeed(2.0)
    assert project.dirty
    project.saveProjectAs(str(tmp_path / "s.mvscene"))
    assert not project.dirty

    # Looking around is not an edit.
    app.viewport2D.panBy(30.0, 10.0)
    app.viewport3D.orbitBy(10.0, 5.0)
    app.animation.setProgress(0.7)
    app.workspace.setWorkspaceMode("3d")
    assert not project.dirty
    del identifier


def test_save_without_a_file_asks_for_one() -> None:
    _, app = make_app()
    assert not app.project.hasFilePath
    assert app.project.saveProject() is False


def test_failed_open_keeps_the_current_document_and_explains(tmp_path) -> None:
    document, app = make_app(recent=RecentProjects())
    app.scene.addVector()
    broken = tmp_path / "broken.mvscene"
    broken.write_text("{not json", encoding="utf-8")

    assert not app.project.openProject(str(broken))
    assert "broken.mvscene is damaged" in app.errorMessage
    assert len(document.vectors) == 1 and app.project.dirty


def test_missing_recent_project_is_dropped_from_the_list(tmp_path) -> None:
    _, app = make_app(recent=RecentProjects())
    path = tmp_path / "gone.mvscene"
    app.project.saveProjectAs(str(path))
    assert [entry["name"] for entry in app.project.recentProjects] == ["gone.mvscene"]

    path.unlink()
    assert not app.project.openProject(str(path))
    assert app.project.recentProjects == []
    assert "no longer exists" in app.errorMessage


def test_undo_and_redo_texts_name_the_edit() -> None:
    _, app = make_app()
    project = app.project
    assert project.undoText == "Undo" and not project.canUndo

    app.scene.addVector()
    app.transformation.applyPreset("rotation")
    assert project.undoText == "Undo Edit A"
    assert project.undo()
    assert project.undoText == "Undo Add u" and project.redoText == "Redo Edit A"
    assert project.redo()
    assert app.document.matrix == Matrix2(0, -1, 1, 0)


def test_recovery_snapshot_is_written_only_for_unsaved_work_and_restored(tmp_path) -> None:
    recovery_dir = tmp_path / "recovery"
    store = RecoveryStore(recovery_dir)
    document, app = make_app(recovery_dir)
    saved = tmp_path / "work.mvscene"
    app.project.saveProjectAs(str(saved))

    app.project.writeRecoverySnapshot()
    assert not store.exists()

    app.scene.addVector()
    app.transformation.applyPreset("scale")
    app.project.writeRecoverySnapshot()
    assert store.exists()
    expected = SceneDocument()
    expected.replace_contents(document)

    # The application "crashed"; the next session finds the snapshot.
    restored_document, restarted = make_app(recovery_dir)
    assert restarted.project.recoveryAvailable
    assert restarted.project.restoreRecovery()
    assert restored_document == expected
    assert restarted.project.dirty and restarted.project.filePath == str(saved)
    assert not restarted.project.recoveryAvailable

    restarted.project.saveProject()
    assert not store.exists()


def test_discarding_recovery_and_quitting_cleanly_remove_the_snapshot(tmp_path) -> None:
    store = RecoveryStore(tmp_path)
    store.write(SceneDocument(), None)
    _, app = make_app(tmp_path)
    assert app.project.recoveryAvailable

    app.scene.addVector()
    # A pending snapshot from the crash is never overwritten by new work.
    app.project.writeRecoverySnapshot()
    assert store.read().document.vectors == []

    app.project.discardRecovery()
    assert not store.exists() and not app.project.recoveryAvailable
    app.project.writeRecoverySnapshot()
    assert store.exists()
    app.project.prepareToQuit()
    assert not store.exists()


def test_new_project_clears_history_and_file(tmp_path) -> None:
    document, app = make_app()
    app.scene.addVector()
    app.project.saveProjectAs(str(tmp_path / "a.mvscene"))
    app.project.newProject()

    assert app.project.filePath == "" and not app.project.canUndo and not app.project.dirty
    assert document.title == "Untitled"
    assert Path(tmp_path / "a.mvscene").exists()
