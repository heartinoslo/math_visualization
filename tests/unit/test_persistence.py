"""Tests for project files, the schema policy, recent projects, recovery and dirty tracking."""

import json
import os

import pytest
from PySide6.QtCore import QSettings

from math_visualization.commands import AddVectorCommand, CommandManager, UpdateMatrixCommand, UpdateVectorCommand
from math_visualization.math_core import Matrix2, Vector2
from math_visualization.persistence import project_file
from math_visualization.persistence.project_file import (
    FILE_FORMAT,
    ProjectFileError,
    read_project,
    upgrade,
    write_project,
)
from math_visualization.persistence.recent_projects import (
    MAX_RECENT_PROJECTS,
    RecentProjects,
    SettingsStorage,
)
from math_visualization.persistence.recovery import RecoveryStore
from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.matrix_object import MatrixObject
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import VectorObject
from math_visualization.scene.visual_state import VisualState
from math_visualization.scene.workspace_state import CameraState2D, CameraState3D, ProjectionMode, WorkspaceMode


def full_document() -> SceneDocument:
    vectors = [
        VectorObject("a1", "u", "#FF862F", Vector2(2.0, -1.5)),
        VectorObject("b2", "v", "#D147BD", Vector2(0.25, 3.0)),
    ]
    return SceneDocument(
        title="Shear demo",
        workspace_mode=WorkspaceMode.THREE_D,
        workspace_state_2d=CameraState2D(center_x=1.5, center_y=-2.0, zoom=2.5),
        workspace_state_3d=CameraState3D(
            target_x=1.0, target_y=2.0, target_z=0.5, azimuth=30.0, elevation=40.0, distance=8.0,
            projection_mode=ProjectionMode.ORTHOGRAPHIC,
        ),
        animation_state=AnimationState(progress=0.4, rate_function="linear", playback_speed=2.0),
        vectors=vectors,
        selected_object_id="b2",
        visual_state=VisualState(show_ghosts=False, show_kernel=False),
        matrices=[MatrixObject("m1", "A", Matrix2(1.0, 1.0, 0.0, 1.0)), MatrixObject("m2", "B", Matrix2(0, -1, 1, 0))],
        active_matrix_id="m2",
    )


def write_raw(path, data) -> None:
    path.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")


def valid_data(tmp_path) -> dict:
    write_project(full_document(), tmp_path / "base.mvscene")
    return json.loads((tmp_path / "base.mvscene").read_text(encoding="utf-8"))


# Round trip ---------------------------------------------------------------------


def test_save_and_reopen_restores_everything(tmp_path) -> None:
    document = full_document()
    path = tmp_path / "scene.mvscene"

    write_project(document, path)
    reopened = read_project(path)

    assert reopened == document
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"] == FILE_FORMAT and data["schema_version"] == 2


def test_failed_write_keeps_the_previous_file_and_leaves_no_temporary(tmp_path, monkeypatch) -> None:
    path = tmp_path / "scene.mvscene"
    write_project(SceneDocument(title="first"), path)
    before = path.read_bytes()

    def broken_replace(*_):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(ProjectFileError, match="No space left"):
        write_project(full_document(), path)

    assert path.read_bytes() == before
    assert sorted(item.name for item in tmp_path.iterdir()) == ["scene.mvscene"]


def test_unwritable_location_is_a_friendly_error(tmp_path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(ProjectFileError, match="Could not save"):
        write_project(SceneDocument(), blocker / "scene.mvscene")


# Damaged and foreign files never crash ---------------------------------------------


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "invalid JSON"),
        ('{"format": "math-visualization-scene", "schema', "invalid JSON at line 1"),
        ("[1, 2, 3]", "not a Math Visualization scene"),
        ('{"name": "something else"}', "not a Math Visualization scene"),
        (b"\x89PNG\r\n\x1a\n\x00\xff", "not UTF-8"),
    ],
)
def test_corrupt_or_foreign_content(tmp_path, content, message) -> None:
    path = tmp_path / "bad.mvscene"
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    with pytest.raises(ProjectFileError, match=message):
        read_project(path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d["matrices"][0].update(entries=[[1, 2, 3], [4, 5, 6]]), "matrix must be 2x2"),
        (lambda d: d["matrices"][0].update(size=4), "unsupported matrix size"),
        (lambda d: d["matrices"][0].update(size=3), "matrix must be 3x3"),
        (lambda d: d.update(active_operation_id="nope"), "active_operation_id"),
        (lambda d: d.update(active_matrix_id="nope"), "active_matrix_id"),
        (lambda d: d["matrices"][1].update(id=d["matrices"][0]["id"]), "matrix ids must be unique"),
        (lambda d: d["vectors"][0].update(components=["1", 2]), "expected a number"),
        (lambda d: d.pop("vectors"), "vectors"),
        (lambda d: d.update(selected_object_id="ghost"), "selected_object_id"),
        (lambda d: d["animation"].update(progress=7), "progress"),
        (lambda d: d["visual_state"].update(show_kernel="yes"), "show_kernel"),
    ],
)
def test_damaged_fields_are_reported(tmp_path, change, message) -> None:
    data = valid_data(tmp_path)
    change(data)
    path = tmp_path / "damaged.mvscene"
    write_raw(path, data)
    with pytest.raises(ProjectFileError, match=f"damaged.mvscene is damaged: .*{message}"):
        read_project(path)


def test_non_finite_numbers_are_rejected(tmp_path) -> None:
    text = json.dumps(valid_data(tmp_path)).replace('"zoom": 2.5', '"zoom": NaN')
    path = tmp_path / "nan.mvscene"
    write_raw(path, text)
    with pytest.raises(ProjectFileError, match="NaN is not a valid number"):
        read_project(path)


def test_missing_and_oversized_files(tmp_path, monkeypatch) -> None:
    with pytest.raises(ProjectFileError, match="no longer exists"):
        read_project(tmp_path / "gone.mvscene")
    path = tmp_path / "big.mvscene"
    write_project(SceneDocument(), path)
    monkeypatch.setattr(project_file, "MAX_FILE_BYTES", 10)
    with pytest.raises(ProjectFileError, match="too large"):
        read_project(path)


# Schema policy --------------------------------------------------------------------


def test_newer_schema_is_refused_with_an_explanation(tmp_path) -> None:
    data = valid_data(tmp_path)
    data["schema_version"] = 99
    path = tmp_path / "future.mvscene"
    write_raw(path, data)
    with pytest.raises(ProjectFileError, match="newer version .* update the application"):
        read_project(path)


@pytest.mark.parametrize("version", [0, -1, "1", True, None])
def test_invalid_schema_version(tmp_path, version) -> None:
    data = valid_data(tmp_path)
    data["schema_version"] = version
    with pytest.raises(ProjectFileError, match="schema_version"):
        upgrade(data)


def test_older_schemas_are_migrated_step_by_step(tmp_path, monkeypatch) -> None:
    # Pretend this build reads format 3 and knows how to upgrade 1 → 2 → 3.
    monkeypatch.setattr(project_file, "CURRENT_SCHEMA_VERSION", 3)
    steps = []
    monkeypatch.setattr(
        project_file,
        "MIGRATIONS",
        {1: lambda d: steps.append(1) or {**d, "added_in_2": True}, 2: lambda d: steps.append(2) or d},
    )
    upgraded = upgrade({"schema_version": 1})

    assert steps == [1, 2]
    assert upgraded == {"schema_version": 3, "added_in_2": True}


def test_missing_migration_is_a_clear_refusal(monkeypatch) -> None:
    monkeypatch.setattr(project_file, "CURRENT_SCHEMA_VERSION", 2)
    monkeypatch.setattr(project_file, "MIGRATIONS", {})
    with pytest.raises(ProjectFileError, match="format 1, which can no longer be opened"):
        upgrade({"schema_version": 1})


# Recent projects -------------------------------------------------------------------


def test_recent_projects_are_most_recent_first_unique_and_capped(tmp_path) -> None:
    recent = RecentProjects()
    for index in range(MAX_RECENT_PROJECTS + 3):
        recent.add(str(tmp_path / f"p{index}.mvscene"))
    recent.add(str(tmp_path / "p5.mvscene"))

    paths = recent.paths()
    assert len(paths) == MAX_RECENT_PROJECTS
    assert paths[0].endswith("p5.mvscene")
    assert len(set(paths)) == len(paths)

    recent.remove(paths[0])
    assert all(not path.endswith("p5.mvscene") for path in recent.paths())
    recent.clear()
    assert recent.paths() == []


def test_recent_projects_persist_in_settings(tmp_path) -> None:
    settings_path = str(tmp_path / "settings.ini")
    first = RecentProjects(SettingsStorage(QSettings(settings_path, QSettings.IniFormat)))
    first.add(str(tmp_path / "only.mvscene"))

    reopened = RecentProjects(SettingsStorage(QSettings(settings_path, QSettings.IniFormat)))
    assert reopened.paths() == [str(tmp_path / "only.mvscene")]


# Recovery --------------------------------------------------------------------------


def test_recovery_snapshot_round_trip_and_discard(tmp_path) -> None:
    store = RecoveryStore(tmp_path)
    assert not store.exists()

    document = full_document()
    store.write(document, "/projects/demo.mvscene")
    recovered = store.read()
    assert recovered.document == document
    assert recovered.original_path == "/projects/demo.mvscene"
    assert recovered.saved_at

    store.discard()
    assert not store.exists()


def test_damaged_recovery_snapshot_is_an_error_not_a_crash(tmp_path) -> None:
    store = RecoveryStore(tmp_path)
    store.path.write_text("{", encoding="utf-8")
    with pytest.raises(ProjectFileError):
        store.read()


# Dirty tracking in the history ---------------------------------------------------------


def vector(name="u", x=1.0) -> VectorObject:
    return VectorObject(f"id-{name}", name, "#FF862F", Vector2(x, 1.0))


def test_history_is_clean_exactly_at_the_saved_point() -> None:
    document = SceneDocument()
    commands = CommandManager(document)
    assert commands.is_clean

    commands.execute(AddVectorCommand(vector()))
    assert not commands.is_clean
    commands.mark_clean()
    assert commands.is_clean

    active = document.active_matrix
    commands.execute(UpdateMatrixCommand(active, MatrixObject(active.object_id, "A", Matrix2(2, 0, 0, 2))))
    assert not commands.is_clean
    commands.undo()
    assert commands.is_clean
    commands.undo()
    assert not commands.is_clean
    commands.redo()
    assert commands.is_clean


def test_saved_point_lost_by_a_new_branch_stays_dirty() -> None:
    document = SceneDocument()
    commands = CommandManager(document)
    commands.execute(AddVectorCommand(vector()))
    commands.mark_clean()
    commands.undo()
    commands.execute(AddVectorCommand(vector("v")))
    commands.undo()

    assert not commands.is_clean


def test_merging_into_the_saved_edit_makes_it_dirty() -> None:
    document = SceneDocument()
    commands = CommandManager(document)
    commands.execute(AddVectorCommand(vector()))
    start = vector()
    commands.execute(UpdateVectorCommand(start, vector(x=2.0), "drag"))
    commands.mark_clean()

    commands.execute(UpdateVectorCommand(vector(x=2.0), vector(x=3.0), "drag"))
    assert not commands.is_clean
    commands.undo()
    commands.redo()
    assert not commands.is_clean


def test_clear_forgets_history_and_is_clean() -> None:
    commands = CommandManager(SceneDocument())
    commands.execute(AddVectorCommand(vector()))
    commands.clear()
    assert commands.is_clean and not commands.can_undo and not commands.can_redo


def test_history_labels_name_the_edit() -> None:
    document = SceneDocument()
    commands = CommandManager(document)
    commands.execute(AddVectorCommand(vector()))
    assert commands.undo_label == "Add u"
    renamed = VectorObject("id-u", "w", "#FF862F", Vector2(1.0, 1.0))
    commands.execute(UpdateVectorCommand(vector(), renamed))
    assert commands.undo_label == "Rename u"
    commands.undo()
    assert commands.redo_label == "Rename u" and commands.undo_label == "Add u"


# Schema 1 → 2: one matrix becomes the named matrix "A" ------------------------------------


def version_1_data(tmp_path) -> dict:
    """A Stage 7 (schema 1) file: the same keys, but one plain ``matrix``."""
    data = valid_data(tmp_path)
    data.pop("matrices")
    data.pop("active_matrix_id")
    data["schema_version"] = 1
    data["matrix"] = [[2.0, 0.0], [0.0, 0.5]]
    return data


def test_version_1_files_open_with_their_matrix_as_a(tmp_path) -> None:
    path = tmp_path / "old.mvscene"
    write_raw(path, version_1_data(tmp_path))

    document = read_project(path)

    assert [matrix.name for matrix in document.matrices] == ["A"]
    assert document.active_matrix_id == document.matrices[0].object_id
    assert document.matrix == Matrix2(2.0, 0.0, 0.0, 0.5)
    assert [vector.name for vector in document.vectors] == ["u", "v"]
    # Saving writes the current format.
    write_project(document, path)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2


def test_version_1_file_without_matrix_is_damaged(tmp_path) -> None:
    data = version_1_data(tmp_path)
    data.pop("matrix")
    path = tmp_path / "old.mvscene"
    write_raw(path, data)
    with pytest.raises(ProjectFileError, match="old.mvscene is damaged: matrix is missing"):
        read_project(path)


def test_recovery_snapshot_from_version_1_is_upgraded(tmp_path) -> None:
    data = version_1_data(tmp_path)
    data["recovery"] = {"original_path": None, "saved_at": "2026-10-01T10:00:00"}
    write_raw(tmp_path / "recovery.mvscene", data)

    assert RecoveryStore(tmp_path).read().document.matrix == Matrix2(2.0, 0.0, 0.0, 0.5)


def test_documents_without_matrices_round_trip(tmp_path) -> None:
    document = SceneDocument(matrices=[])
    assert document.active_matrix_id is None and document.matrix == Matrix2.identity()
    write_project(document, tmp_path / "empty.mvscene")
    assert read_project(tmp_path / "empty.mvscene") == document
