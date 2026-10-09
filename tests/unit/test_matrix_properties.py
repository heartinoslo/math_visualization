"""Tests for the matrix properties view model and the determinant feedback geometry."""

import pytest

from math_visualization.math_core import Matrix2
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.viewmodels.application_viewmodel import ApplicationViewModel
from math_visualization.viewmodels.formatting import format_quantity


def make_app(entries=None, progress=1.0):
    document = SceneDocument()
    app = ApplicationViewModel(document)
    app.viewport2D.setViewportSize(800.0, 600.0)
    app.viewport3D.setViewportSize(900.0, 600.0)
    if entries is not None:
        app.transformation.set_matrix(Matrix2(*entries))
    app.animation.setProgress(progress)
    return document, app


def set_rate_linear(app) -> None:
    app.animation.setRateFunction("linear")


def test_format_quantity_never_rounds_small_values_to_zero() -> None:
    assert format_quantity(2.0) == "2"
    assert format_quantity(-0.5) == "-0.5"
    assert format_quantity(1e-4) == "1e-4"
    assert format_quantity(-2.5e-7) == "-2.5e-7"
    assert format_quantity(1.234e8) == "1.234e8"
    assert format_quantity(0.0) == "0"
    assert format_quantity(float("inf")) == "∞"


def test_regular_matrix_properties() -> None:
    _, app = make_app((1, 2, 3, 4))
    properties = app.matrixProperties

    assert properties.determinantText == "-2"
    assert properties.areaScaleText == "×2"
    assert properties.orientation == "reversed"
    assert properties.rank == 2 and properties.invertible
    assert properties.status == "regular"
    assert properties.inverseEntryTexts == ["-2", "1", "1.5", "-0.5"]
    assert properties.determinantFormula == "det A = ad − bc = 1·4 − 2·3 = -2"
    assert properties.rankFormula.startswith("rank A = 2  (invertible")


def test_singular_and_near_singular_status() -> None:
    _, app = make_app((1, 2, 0.5, 1))
    properties = app.matrixProperties
    assert properties.status == "singular" and properties.rank == 1
    assert properties.orientation == "collapsed"
    assert properties.inverseEntryTexts == [] and properties.conditionText == "∞"
    assert "line" in properties.statusDetail

    app.transformation.setEntryText(3, "1.0001")
    assert properties.status == "near_singular" and properties.invertible
    assert "κ" in properties.statusDetail
    # The tiny determinant is shown, not rounded away.
    assert properties.determinantText == "1e-4"

    app.transformation.set_matrix(Matrix2(0, 0, 0, 0))
    assert properties.rank == 0 and "origin" in properties.statusDetail


def test_negative_entries_are_parenthesised_in_the_formula() -> None:
    _, app = make_app((-1, 2, -3, 0.5))
    assert app.matrixProperties.determinantFormula == "det A = ad − bc = (-1)·0.5 − 2·(-3) = 5.5"


def test_apply_inverse_is_undoable_and_refused_for_singular_matrices() -> None:
    document, app = make_app((2, 1, 1, 1))

    assert app.matrixProperties.applyInverse()
    assert document.matrix == Matrix2(1, -1, -1, 2)
    app.scene.undo()
    assert document.matrix == Matrix2(2, 1, 1, 1)

    app.transformation.applyPreset("singular")
    assert not app.matrixProperties.applyInverse()
    assert document.matrix == Matrix2(1, 2, 0.5, 1)
    assert "no inverse" in app.errorMessage


def test_live_determinant_follows_a_of_t() -> None:
    _, app = make_app((1, 0, 0, -1), progress=0.0)
    set_rate_linear(app)
    seen = []
    app.matrixProperties.currentChanged.connect(lambda: seen.append(app.matrixProperties.currentDeterminantText))

    for progress in (0.25, 0.5, 1.0):
        app.animation.setProgress(progress)

    assert seen == ["det = 0.5", "det = 0", "det = -1"]


# 2D feedback ----------------------------------------------------------------------


def test_2d_reflection_flips_only_once_det_turns_negative() -> None:
    _, app = make_app((1, 0, 0, -1), progress=0.0)
    set_rate_linear(app)

    app.animation.setProgress(0.25)
    overlay = app.viewport2D.determinantOverlay
    assert not overlay["flipped"] and overlay["arc"] and not overlay["imageLine"]

    # Halfway A(t) = diag(1, 0): the plane is squashed onto the x-axis.
    app.animation.setProgress(0.5)
    overlay = app.viewport2D.determinantOverlay
    assert not overlay["flipped"] and not overlay["arc"]
    x1, y1, x2, y2 = overlay["imageLine"]
    assert y1 == pytest.approx(300.0) and y2 == pytest.approx(300.0)

    app.animation.setProgress(1.0)
    overlay = app.viewport2D.determinantOverlay
    assert overlay["flipped"] and overlay["arc"] and len(overlay["arcHead"]) == 6


def test_2d_arc_turns_clockwise_on_screen_when_flipped() -> None:
    def screen_turn(entries) -> float:
        _, app = make_app(entries)
        arc = app.viewport2D.determinantOverlay["arc"]
        points = list(zip(arc[0::2], arc[1::2]))
        return sum(
            (x1 - 400) * (y2 - 300) - (x2 - 400) * (y1 - 300) for (x1, y1), (x2, y2) in zip(points, points[1:])
        )

    # Screen y points down, so a counter-clockwise math turn is negative on screen.
    assert screen_turn((1, 0, 0, 1)) < 0
    assert screen_turn((1, 0, 0, -1)) > 0


def test_2d_kernel_line_and_toggles() -> None:
    document, app = make_app((1, 0, 0, 0), progress=0.0)
    overlay = app.viewport2D.determinantOverlay
    # The kernel of the projection is the y-axis, shown even before playing.
    x1, y1, x2, y2 = overlay["kernelLine"]
    assert x1 == pytest.approx(400.0) and x2 == pytest.approx(400.0)
    assert overlay["imageLine"] == []

    app.transformation.setVisualFlag("show_kernel", False)
    assert app.viewport2D.determinantOverlay["kernelLine"] == []

    app.transformation.applyPreset("rotation")
    app.transformation.setVisualFlag("show_orientation_arc", False)
    app.animation.setProgress(1.0)
    assert app.viewport2D.determinantOverlay["arc"] == []
    assert document.visual_state.show_flip_tint


def test_2d_zero_matrix_collapses_to_the_origin() -> None:
    _, app = make_app((0, 0, 0, 0))
    overlay = app.viewport2D.determinantOverlay
    assert overlay["collapsedToOrigin"] and overlay["imageLine"] == [] and overlay["kernelLine"] == []


def test_2d_determinant_label_sits_at_the_square_centre() -> None:
    _, app = make_app((2, 0, 0, 1))
    overlay = app.viewport2D.determinantOverlay
    assert (overlay["labelX"], overlay["labelY"]) == pytest.approx((400 + 80, 300 - 40))


# 3D feedback ----------------------------------------------------------------------


def triangles(flat):
    return [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]


def test_3d_overlay_matches_the_2d_states() -> None:
    _, app = make_app((1, 0, 0, 0))
    overlay = app.viewport3D.determinantOverlay

    assert overlay["arcVertices"] == [] and not overlay["flipped"]
    image = triangles(overlay["imageLineVertices"])
    kernel = triangles(overlay["kernelVertices"])
    assert image and kernel and len(kernel) % 3 == 0
    # Image along x, kernel along y, both flat in the plane just above it.
    assert max(abs(y) for _, y, _ in image) < 0.1 < max(abs(x) for x, _, _ in image)
    assert max(abs(x) for x, _, _ in kernel) < 0.1 < max(abs(y) for _, y, _ in kernel)
    assert len({z for *_, z in image + kernel}) == 1 and image[0][2] > 0

    app.transformation.applyPreset("reflection")
    overlay = app.viewport3D.determinantOverlay
    assert overlay["flipped"] and overlay["arcVertices"] and overlay["kernelVertices"] == []
    assert overlay["labelVisible"]


def test_3d_kernel_dashes_stay_bounded_far_from_the_origin() -> None:
    _, app = make_app((1, 0, 0, 0))
    for _ in range(30):
        app.viewport3D.zoomBy(-1200.0)
    app.viewport3D.panBy(-4000.0, 0.0)

    kernel = app.viewport3D.determinantOverlay["kernelVertices"]
    assert 0 < len(kernel) // (6 * 3) <= 402
