"""Tests for playback, the transformation view model and transformed geometry."""

import math

import pytest

from math_visualization.commands import CommandManager
from math_visualization.math_core import Matrix2, Vector2
from math_visualization.math_core.manim_port import I_HAT_COLOR, J_HAT_COLOR, smooth
from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.serialization import SceneFormatError, document_from_dict, document_to_dict
from math_visualization.scene.visual_state import VisualState
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel
from math_visualization.viewport.transformation_geometry import (
    MAX_LINES_PER_SIDE,
    clip_segment,
    lines_per_side,
    smallest_singular_value,
    transformed_grid,
    unit_square,
)


def make_app():
    document = SceneDocument()
    app = ApplicationViewModel(document)
    app.viewport2D.setViewportSize(800.0, 600.0)
    return document, app


def record(signal) -> list:
    emissions: list = []
    signal.connect(lambda *arguments: emissions.append(arguments))
    return emissions


# Playback ---------------------------------------------------------------------------


def test_playback_advances_with_speed_and_stops_at_the_end() -> None:
    document, app = make_app()
    animation = app.animation

    animation.advance(0.5)
    assert animation.progress == 0.0  # paused: time does not move

    animation.play()
    animation.advance(0.5)
    assert animation.progress == pytest.approx(0.25)
    animation.setPlaybackSpeed(2.0)
    animation.advance(0.5)
    assert animation.progress == pytest.approx(0.75)
    animation.advance(5.0)
    assert animation.progress == 1.0
    assert animation.playing is False


def test_play_at_the_end_restarts_and_reset_rewinds() -> None:
    _, app = make_app()
    animation = app.animation
    animation.setProgress(1.0)

    animation.play()
    assert animation.progress == 0.0 and animation.playing

    animation.advance(1.0)
    animation.reset()
    assert animation.progress == 0.0 and not animation.playing


def test_scrubbing_pauses_and_clamps() -> None:
    _, app = make_app()
    animation = app.animation
    animation.play()

    animation.scrub(1.7)

    assert animation.progress == 1.0
    assert animation.playing is False


def test_eased_progress_uses_the_rate_function() -> None:
    _, app = make_app()
    animation = app.animation
    animation.setProgress(0.25)

    assert animation.easedProgress == pytest.approx(smooth(0.25))
    animation.setRateFunction("linear")
    assert animation.easedProgress == pytest.approx(0.25)


def test_invalid_settings_are_reported() -> None:
    _, app = make_app()

    app.animation.setPlaybackSpeed(3.0)
    assert "playback_speed" in app.errorMessage
    app.animation.setRateFunction("bounce")
    assert "rate function" in app.errorMessage
    assert app.animation.playbackSpeed == 1.0 and app.animation.rateFunction == "smooth"


# Transformation view model -----------------------------------------------------------------


def test_presets_and_entries_go_through_undoable_commands() -> None:
    document, app = make_app()
    transformation = app.transformation
    changes = record(transformation.matrixChanged)

    assert transformation.applyPreset("shear")
    assert document.matrix == Matrix2(1, 1, 0, 1)
    assert transformation.setEntryText(2, " −0.5 ")
    assert transformation.entryTexts == ["1", "1", "-0.5", "1"]
    assert len(changes) == 2

    assert app.scene.undo()
    assert document.matrix == Matrix2(1, 1, 0, 1)
    assert app.scene.undo()
    assert document.matrix == Matrix2.identity()
    assert app.scene.canRedo


def test_bad_entries_and_unknown_presets_are_rejected() -> None:
    document, app = make_app()

    assert not app.transformation.setEntryText(1, "abc")
    assert "Matrix entry a₁₂" in app.errorMessage
    assert not app.transformation.applyPreset("spin")
    assert document.matrix == Matrix2.identity()


def test_current_matrix_follows_the_eased_progress() -> None:
    document, app = make_app()
    transformation = app.transformation
    changes = record(transformation.currentMatrixChanged)
    transformation.applyPreset("rotation")
    assert transformation.current_matrix() == Matrix2.identity()

    app.animation.setProgress(0.5)
    t = smooth(0.5)
    assert transformation.current_matrix() == Matrix2(1 - t, -t, t, 1 - t)
    app.animation.setProgress(1.0)
    assert transformation.current_matrix() == document.matrix
    assert len(changes) == 2


def test_expression_texts() -> None:
    _, app = make_app()
    transformation = app.transformation
    identifier = app.scene.addVector()
    app.scene.setComponents(identifier, 2.0, 1.0)
    transformation.applyPreset("scale")
    app.animation.setProgress(1.0)

    assert transformation.targetText == "A = [ 2  0 ; 0  0.5 ]"
    assert transformation.parameterText.startswith("t = smooth(τ) = 1.000")
    assert transformation.currentText.endswith("[ 2  0 ; 0  0.5 ]")
    assert transformation.selectedMappingText == "A(t)·u = A(t)·(2, 1) = (4, 0.5)"


def test_visual_flags() -> None:
    document, app = make_app()

    app.transformation.setVisualFlag("show_unit_square", False)
    assert document.visual_state.show_unit_square is False
    assert app.transformation.visualState["show_unit_square"] is False
    app.transformation.setVisualFlag("show_everything", True)
    assert "Unknown display option" in app.errorMessage


# Serialization of the new state -------------------------------------------------------------


def test_matrix_animation_and_visual_state_round_trip() -> None:
    document = SceneDocument()
    document.matrix = Matrix2(1, 2, 0.5, 1)
    document.animation_state = AnimationState(0.4, 2.0, "linear", 0.5)
    document.visual_state = VisualState(show_ghosts=False)

    data = document_to_dict(document)

    assert data["matrices"][0]["entries"] == [[1.0, 2.0], [0.5, 1.0]]
    assert data["animation"]["interpolation"] == "identity_to_target"
    assert document_from_dict(data) == document
    data["matrices"][0]["entries"] = [[1.0, 2.0]]
    with pytest.raises(SceneFormatError):
        document_from_dict(data)


# Geometry -------------------------------------------------------------------------------------


def test_smallest_singular_value_is_accurate_for_close_singular_values() -> None:
    # Equal singular values are where subtracting square roots cancels badly.
    for matrix in (Matrix2.identity(), Matrix2(0, -1, 1, 0), Matrix2(3, 0, 0, 3.000001)):
        expected = min(abs(matrix.a), abs(matrix.d)) if matrix.b == 0 else 1.0
        assert smallest_singular_value(matrix) == pytest.approx(expected, rel=1e-14)


def test_singular_values_and_line_counts() -> None:
    assert smallest_singular_value(Matrix2(2, 0, 0, 0.5)) == pytest.approx(0.5)
    assert smallest_singular_value(Matrix2(0, -1, 1, 0)) == pytest.approx(1.0)
    assert smallest_singular_value(Matrix2(1, 2, 0.5, 1)) == pytest.approx(0.0, abs=1e-9)
    assert lines_per_side(Matrix2.identity(), 5.0, 1.0) == 6
    assert lines_per_side(Matrix2(1, 0, 0, 0), 5.0, 1.0) == MAX_LINES_PER_SIDE


def test_transformed_grid_maps_lattice_lines_and_survives_singular_matrices() -> None:
    lines, axes = transformed_grid(Matrix2(0, -1, 1, 0), 1.0, 2)

    assert len(lines) == 8 and len(axes) == 2
    # Rotating x = 1 by 90° gives y = 1.
    assert any(abs(start[1] - 1.0) < 1e-12 and abs(end[1] - 1.0) < 1e-12 for start, end in lines)
    _, zero_axes = transformed_grid(Matrix2(0, 0, 0, 0), 1.0, 2)
    assert zero_axes == []
    projected, _ = transformed_grid(Matrix2(1, 0, 0, 0), 1.0, 2)
    assert all(start[1] == end[1] == 0.0 for start, end in projected)


def test_unit_square_is_spanned_by_the_columns() -> None:
    corners = unit_square(Matrix2(2, 1, 0, 1))

    assert corners == [(0.0, 0.0), (2.0, 0.0), (3.0, 1.0), (1.0, 1.0)]


def test_clipping() -> None:
    assert clip_segment(((-10.0, 5.0), (10.0, 5.0)), 0, 0, 8, 8) == ((0.0, 5.0), (8.0, 5.0))
    assert clip_segment(((-10.0, 50.0), (10.0, 50.0)), 0, 0, 8, 8) is None
    assert clip_segment(((1.0, 1.0), (2.0, 2.0)), 0, 0, 8, 8) == ((1.0, 1.0), (2.0, 2.0))


# 2D viewport with a transformation -------------------------------------------------------------


def test_2d_vectors_are_drawn_transformed_with_input_ghosts() -> None:
    document, app = make_app()
    identifier = app.scene.addVector()
    app.scene.setComponents(identifier, 1.0, 0.0)
    app.transformation.applyPreset("rotation")
    app.animation.setProgress(1.0)

    shape = app.viewport2D.vectorShapes[0]
    assert (shape["tipX"], shape["tipY"]) == pytest.approx((400.0, 300.0 - 80.0))
    assert (shape["ghostX"], shape["ghostY"]) == pytest.approx((480.0, 300.0))
    assert shape["showGhost"] is True
    app.transformation.setVisualFlag("show_ghosts", False)
    assert app.viewport2D.vectorShapes[0]["showGhost"] is False


def test_2d_dragging_moves_the_input_vector_while_transformed() -> None:
    document, app = make_app()
    identifier = app.scene.addVector()
    app.scene.setComponents(identifier, 1.0, 0.0)
    app.transformation.applyPreset("scale")
    app.animation.setProgress(1.0)
    viewport = app.viewport2D

    assert viewport.hitTest(560.0, 300.0)["part"] == "shaft"  # transformed tip (2, 0) selects
    assert viewport.beginVectorDrag(480.0, 300.0) == "tip"  # the ghost (input) is the handle
    viewport.dragVector(480.0, 220.0, False)
    viewport.endVectorDrag()

    assert document.vectors[0].vector == Vector2(1, 1)
    assert viewport.vectorShapes[0]["tipX"] == pytest.approx(400.0 + 2 * 80.0)
    assert viewport.vectorShapes[0]["tipY"] == pytest.approx(300.0 - 0.5 * 80.0)


def test_2d_basis_square_and_grid_follow_the_current_matrix() -> None:
    _, app = make_app()
    viewport = app.viewport2D
    app.transformation.applyPreset("shear")
    app.animation.setProgress(1.0)

    i_hat, j_hat = viewport.basisVectors
    assert (i_hat["label"], i_hat["color"], j_hat["color"]) == ("î", I_HAT_COLOR, J_HAT_COLOR)
    assert (j_hat["tipX"], j_hat["tipY"]) == pytest.approx((480.0, 220.0))
    assert viewport.unitSquare == pytest.approx([400, 300, 480, 300, 560, 220, 480, 220])
    lines = viewport.transformedGridLines
    assert len(lines) % 4 == 0 and lines
    assert all(-4.0 <= x <= 804.0 for x in lines[0::2]) and all(-4.0 <= y <= 604.0 for y in lines[1::2])


def test_2d_singular_matrix_keeps_working() -> None:
    _, app = make_app()
    app.scene.addVector()
    app.transformation.applyPreset("projection")
    app.animation.setProgress(1.0)
    viewport = app.viewport2D

    j_hat = viewport.basisVectors[1]
    assert j_hat["isZero"] is True
    assert viewport.transformedGridLines is not None
    ys = viewport.transformedGridLines[1::2]
    assert all(y == pytest.approx(300.0) for y in ys)
