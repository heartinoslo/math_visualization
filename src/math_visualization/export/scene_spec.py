"""The scene specification: everything a Manim export needs, as plain JSON data.

It is built from the document (and the current view framing) once, when an
export starts, so later edits never affect a running render. The generated
ManimGL script reads only this data; it contains no user text as code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from math_visualization.math_core import manim_port
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.workspace_state import WorkspaceMode
from math_visualization.viewport.transformation_geometry import lines_per_side
from math_visualization.viewport.viewport_2d import Viewport2D
from math_visualization.viewport.viewport_3d import Viewport3D


SPEC_VERSION = 1
# Seconds shown before and after the transformation plays.
HOLD_BEFORE = 0.5
HOLD_AFTER = 1.0
VIDEO_ASPECT = 16 / 9
DEFAULT_FRAME_HEIGHT = 8.0
BACKGROUND_COLOR = "#12161C"


@dataclass(frozen=True)
class QualityPreset:
    key: str
    label: str
    width: int
    height: int
    fps: int


QUALITY_PRESETS = {
    preset.key: preset
    for preset in (
        QualityPreset("480p", "480p · 30 fps (preview)", 854, 480, 30),
        QualityPreset("1080p", "1080p · 60 fps", 1920, 1080, 60),
    )
}
DEFAULT_QUALITY = "480p"


def total_frames(spec: dict[str, Any], preset: QualityPreset) -> int:
    """Frames ManimGL writes for ``spec``; used to turn its frame counter into a percentage."""
    seconds = spec["hold_before"] + spec["duration"] + spec["hold_after"]
    return max(1, round(seconds * preset.fps))


def _fit_height(visible_width: float, visible_height: float) -> float:
    """Frame height of a 16:9 video that shows the whole visible area."""
    return max(visible_height, visible_width / VIDEO_ASPECT)


def build_scene_spec(
    document: SceneDocument,
    viewport_2d_size: tuple[float, float] = (0.0, 0.0),
    viewport_3d_size: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    """Describe the document for ManimGL, framed like the current views."""
    matrix = document.matrix
    visual = document.visual_state
    animation = document.animation_state
    spec: dict[str, Any] = {
        "spec_version": SPEC_VERSION,
        "title": document.title,
        "mode": "3d" if document.workspace_mode is WorkspaceMode.THREE_D else "2d",
        "matrix": [list(row) for row in matrix.rows],
        "vectors": [
            {"name": vector.name, "color": vector.color, "components": [vector.vector.x, vector.vector.y]}
            for vector in document.vectors
        ],
        "show_grid": visual.show_transformed_grid,
        "show_unit_square": visual.show_unit_square,
        "show_basis": visual.show_basis_vectors,
        "duration": animation.duration,
        "rate_function": animation.rate_function,
        "hold_before": HOLD_BEFORE,
        "hold_after": HOLD_AFTER,
        "colors": {
            "background": BACKGROUND_COLOR,
            "grid": manim_port.FOREGROUND_GRID_COLOR,
            "i_hat": manim_port.I_HAT_COLOR,
            "j_hat": manim_port.J_HAT_COLOR,
            "unit_square": manim_port.UNIT_SQUARE_COLOR,
        },
    }

    view_2d = Viewport2D(document.workspace_state_2d, *viewport_2d_size)
    camera_2d = document.workspace_state_2d
    if view_2d.width > 0.0 and view_2d.height > 0.0:
        units = 1.0 / view_2d.pixels_per_unit
        height = _fit_height(view_2d.width * units, view_2d.height * units)
        step = view_2d.grid().step.major
    else:
        height, step = DEFAULT_FRAME_HEIGHT, 1.0
    spec["frame_2d"] = {"center": [camera_2d.center_x, camera_2d.center_y], "height": height}

    view_3d = Viewport3D(document.workspace_state_3d, *viewport_3d_size)
    camera_3d = document.workspace_state_3d
    # ManimGL orients its frame by z-x-z Euler angles (θ, φ), so the eye lies
    # along (sin θ sin φ, −cos θ sin φ, cos φ). Ours is along
    # (cos e cos a, cos e sin a, sin e), hence θ = a + 90° and φ = 90° − e.
    # Both use a 45° vertical field of view, so the frame height is our
    # visible height at the target.
    spec["camera_3d"] = {
        "theta": camera_3d.azimuth + 90.0,
        "phi": 90.0 - view_3d.elevation,
        "center": list(view_3d.target),
        "height": view_3d.visible_height,
    }
    if spec["mode"] == "3d":
        grid_3d = view_3d.grid()
        step = grid_3d.step.major
        reach = grid_3d.half_extent + math.hypot(grid_3d.center_x, grid_3d.center_y)
    else:
        frame = spec["frame_2d"]
        reach = 0.5 * math.hypot(frame["height"] * VIDEO_ASPECT, frame["height"]) + math.hypot(*frame["center"])
    count = lines_per_side(matrix, reach, step)
    spec["grid"] = {"step": step, "extent": count * step, "background_extent": math.ceil(reach / step) * step}
    return spec

