"""Tests for the Manim export core: scene spec, script generation and process plumbing."""

import ast
import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from math_visualization.export import manim_export
from math_visualization.export.manim_export import (
    SCENE_CLASS,
    interpret_probe,
    parse_frame_count,
    render_command,
    render_config,
    render_script,
    safe_file_stem,
)
from math_visualization.export.scene_spec import QUALITY_PRESETS, build_scene_spec, total_frames
from math_visualization.math_core import Matrix2, Vector2
from math_visualization.scene.animation_state import AnimationState
from math_visualization.scene.scene_document import SceneDocument
from math_visualization.scene.vector_object import VectorObject
from math_visualization.scene.visual_state import VisualState
from math_visualization.scene.workspace_state import CameraState2D, CameraState3D, WorkspaceMode
from math_visualization.viewport.viewport_3d import Viewport3D


def document(**changes) -> SceneDocument:
    base = SceneDocument(
        vectors=[VectorObject("a", "u", "#FF862F", Vector2(2, 1)), VectorObject("b", "v", "#D147BD", Vector2(-1, 0.5))],
        animation_state=AnimationState(duration=3.0, rate_function="linear"),
        visual_state=VisualState(show_unit_square=False),
    )
    base.matrix = Matrix2(1, 1, 0, 1)
    for key, value in changes.items():
        setattr(base, key, value)
    return base


def embedded_spec(script: str) -> dict:
    """The spec as the generated script will see it, found by parsing (not running) the script."""
    for node in ast.walk(ast.parse(script)):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "SPEC":
            call = node.value
            assert isinstance(call, ast.Call) and len(call.args) == 1
            assert isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)
            return json.loads(call.args[0].value)
    raise AssertionError("SPEC not found")


# Scene spec ---------------------------------------------------------------------


def test_spec_carries_the_document() -> None:
    spec = build_scene_spec(document(), (900, 600), (900, 600))

    assert spec["mode"] == "2d"
    assert spec["matrix"] == [[1.0, 1.0], [0.0, 1.0]]
    assert spec["vectors"] == [
        {"name": "u", "color": "#FF862F", "components": [2.0, 1.0]},
        {"name": "v", "color": "#D147BD", "components": [-1.0, 0.5]},
    ]
    assert spec["show_grid"] and spec["show_basis"] and not spec["show_unit_square"]
    assert spec["duration"] == 3.0 and spec["rate_function"] == "linear"


def test_2d_frame_shows_the_whole_visible_view() -> None:
    doc = document(workspace_state_2d=CameraState2D(center_x=1.5, center_y=-2.0, zoom=2.0))
    wide = build_scene_spec(doc, (1600, 400))["frame_2d"]
    tall = build_scene_spec(doc, (600, 900))["frame_2d"]

    # 160 px per unit: 10 × 2.5 units (wide) and 3.75 × 5.625 units (tall).
    assert wide == {"center": [1.5, -2.0], "height": pytest.approx(10 / (16 / 9))}
    assert tall["height"] == pytest.approx(5.625)


@pytest.mark.parametrize(("azimuth", "elevation"), [(-60, 25), (0, 0), (135, -40), (-170, 80), (45, 10)])
def test_3d_camera_angles_reproduce_our_eye_direction(azimuth, elevation) -> None:
    """ManimGL's frame orientation is Rotation.from_euler("zxz", [γ, φ, θ]); its columns are
    the camera's right, up and towards-the-eye axes (CameraFrame.set_euler_angles)."""
    camera = CameraState3D(azimuth=azimuth, elevation=elevation, target_x=1.0, target_y=-2.0, distance=9.0)
    spec = build_scene_spec(document(workspace_mode=WorkspaceMode.THREE_D, workspace_state_3d=camera))["camera_3d"]
    rotation = Rotation.from_euler("zxz", [0.0, spec["phi"], spec["theta"]], degrees=True).as_matrix()
    view = Viewport3D(camera, 900, 600)

    assert rotation[:, 2] == pytest.approx(view.backward, abs=1e-12)
    # Screen right and up agree too, so the picture is not rolled or mirrored.
    assert rotation[:, 0] == pytest.approx(view.right, abs=1e-12)
    assert rotation[:, 1] == pytest.approx(view.up, abs=1e-12)
    focal = 0.5 * spec["height"] / math.tan(math.radians(22.5))
    assert focal == pytest.approx(9.0)
    assert spec["center"] == [1.0, -2.0, 0.0]


def test_grid_covers_the_frame_after_the_transformation() -> None:
    spec = build_scene_spec(document(matrix=Matrix2(0.25, 0, 0, 0.25)), (900, 600))
    frame = spec["frame_2d"]
    half_diagonal = 0.5 * math.hypot(frame["height"] * 16 / 9, frame["height"])
    # Shrinking by 4 needs four times as many lines to still reach the corners.
    assert spec["grid"]["extent"] * 0.25 >= half_diagonal


def test_total_frames_includes_the_holds() -> None:
    spec = build_scene_spec(document())
    assert total_frames(spec, QUALITY_PRESETS["480p"]) == round((0.5 + 3.0 + 1.0) * 30)
    assert total_frames(spec, QUALITY_PRESETS["1080p"]) == round(4.5 * 60)


# Script generation ------------------------------------------------------------------


def test_script_compiles_and_embeds_the_spec_as_data() -> None:
    spec = build_scene_spec(document())
    script = render_script(spec)

    compile(script, "scene.py", "exec")
    assert embedded_spec(script) == spec
    assert f"class {SCENE_CLASS}(Scene)" in script
    assert "__SPEC_JSON__" not in script.split("SPEC = ")[1]


def test_hostile_names_stay_data() -> None:
    title = '"); import os; os.system("echo pwned") #\n\'\'\' """'
    name = '");os.system("x")#'
    doc = document(vectors=[VectorObject("a", name, "#FFFFFF", Vector2(1, 1))], title=title)
    script = render_script(build_scene_spec(doc))

    tree = ast.parse(script)
    assert embedded_spec(script)["vectors"][0]["name"] == name
    assert embedded_spec(script)["title"] == title
    calls = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    assert "system" not in calls


def test_template_needs_exactly_one_placeholder(monkeypatch, tmp_path) -> None:
    broken = tmp_path / "template.py"
    broken.write_text("print('no spec')\n", encoding="utf-8")
    monkeypatch.setattr(manim_export, "TEMPLATE_PATH", broken)
    with pytest.raises(RuntimeError):
        render_script({})


# Process plumbing ---------------------------------------------------------------------


def test_command_and_config() -> None:
    preset = QUALITY_PRESETS["1080p"]
    command = render_command("py", Path("s.py"), Path("c.yml"), Path("out"), "demo", preset)

    assert command[:5] == ["py", "-m", "manimlib", "s.py", SCENE_CLASS]
    assert command[command.index("--resolution") + 1] == "1920x1080"
    assert command[command.index("--file_name") + 1] == "demo"
    assert "--fps" not in command
    assert render_config(preset, "#12161C") == 'camera:\n  fps: 60\n  background_color: "#12161C"\n'


def test_progress_is_read_from_the_frame_counter() -> None:
    output = "x.mp4 0 ApplyMatrix : : 4it [00:01,  2.70it/s]\rx.mp4 0 ApplyMatrix : : 57it [00:03, 27.71it/s]"
    assert parse_frame_count(output) == 57
    assert parse_frame_count("ManimGL v1.7.2") is None


@pytest.mark.parametrize(
    ("name", "stem"),
    [("Shear demo", "Shear demo"), ('a/b\\c:d*?"<>|', "a_b_c_d"), ("...", "scene"), ("", "scene")],
)
def test_safe_file_stem(name, stem) -> None:
    assert safe_file_stem(name) == stem


def test_environment_probe_messages(monkeypatch) -> None:
    monkeypatch.setattr(manim_export.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    assert interpret_probe(0, "1.7.2\n").ok
    assert "tested with 1.7.2" in interpret_probe(0, "1.7.1\n").message
    missing = interpret_probe(1, "importlib.metadata.PackageNotFoundError: No package metadata was found for manimgl")
    assert not missing.ok and "not installed" in missing.message
    assert not interpret_probe(1, "").ok

    monkeypatch.setattr(manim_export.shutil, "which", lambda _: None)
    status = interpret_probe(0, "1.7.2")
    assert not status.ok and "ffmpeg" in status.message


def test_spec_numbers_are_plain_json() -> None:
    spec = build_scene_spec(document(), (900, 600), (900, 600))
    assert json.loads(json.dumps(spec, allow_nan=False)) == spec
    assert all(isinstance(value, float) for row in spec["matrix"] for value in row)
    assert np.isfinite(spec["camera_3d"]["height"])


def test_export_uses_the_active_matrix() -> None:
    from math_visualization.scene.matrix_object import MatrixObject

    doc = document()
    doc.matrices = [MatrixObject("a", "A", Matrix2(1, 1, 0, 1)), MatrixObject("b", "B", Matrix2(0, -1, 1, 0))]
    doc.active_matrix_id = "b"
    assert build_scene_spec(doc)["matrix"] == [[0.0, -1.0], [1.0, 0.0]]
