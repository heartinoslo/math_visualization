"""Turning a scene specification into a ManimGL script and the command that renders it.

ManimGL is never imported here: it runs in its own Python environment (the
user's ``.venv-manim``), started as a separate process, so the application
works without it and a failing render can never take the interface down.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from math_visualization.export.scene_spec import QualityPreset


SCENE_CLASS = "MatrixTransformation"
TEMPLATE_PATH = Path(__file__).with_name("manim_scene_template.py")
SPEC_PLACEHOLDER = "json.loads(__SPEC_JSON__)"
SUPPORTED_MANIMGL = "1.7.2"
# Prints the installed ManimGL version without importing it (importing needs a display).
PROBE_CODE = "import importlib.metadata as m; print(m.version('manimgl'))"
VIDEO_EXTENSION = ".mp4"

# "57it [00:03, 27.71it/s]": the frame count, not the rate (which ends in "it/s").
_FRAME_COUNTER = re.compile(r"(?<![\d.])(\d+)it(?!/s)")
_UNSAFE_FILE_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def render_script(spec: dict[str, Any]) -> str:
    """The ManimGL scene for ``spec``. The spec is embedded as a string literal, never as code."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(SPEC_PLACEHOLDER) != 1:
        raise RuntimeError("The Manim scene template must contain the spec placeholder exactly once")
    literal = repr(json.dumps(spec, ensure_ascii=True, allow_nan=False))
    return template.replace(SPEC_PLACEHOLDER, f"json.loads({literal})")


def safe_file_stem(name: str) -> str:
    stem = _UNSAFE_FILE_CHARACTERS.sub("_", name).strip(" ._")
    return stem or "scene"


def render_config(preset: QualityPreset, background: str) -> str:
    """ManimGL config file (YAML) with the frame rate and background.

    ManimGL 1.7.2 keeps ``--fps`` from the command line as a string and then
    fails dividing by it, so the frame rate goes through the config file.
    """
    return f'camera:\n  fps: {int(preset.fps)}\n  background_color: "{background}"\n'


def render_command(
    python: str, script: Path, config: Path, output_dir: Path, file_stem: str, preset: QualityPreset
) -> list[str]:
    """Arguments for ``python -m manimlib`` writing ``output_dir/file_stem.mp4``."""
    return [
        python, "-m", "manimlib", str(script), SCENE_CLASS,
        "--write_file",
        "--config_file", str(config),
        "--resolution", f"{preset.width}x{preset.height}",
        "--video_dir", str(output_dir),
        "--file_name", file_stem,
    ]


def parse_frame_count(output: str) -> int | None:
    """Last frame count in ManimGL's progress output (``… 42it [00:03, …]``)."""
    matches = _FRAME_COUNTER.findall(output)
    return int(matches[-1]) if matches else None


@dataclass(frozen=True)
class EnvironmentStatus:
    ok: bool
    message: str
    version: str = ""


def interpret_probe(exit_code: int, output: str) -> EnvironmentStatus:
    """Explain the result of running :data:`PROBE_CODE` with the chosen Python."""
    version = output.strip().splitlines()[-1].strip() if output.strip() else ""
    if exit_code != 0 or not re.fullmatch(r"\d+(\.\d+)*\w*", version):
        if "PackageNotFoundError" in output or "No package metadata" in output:
            return EnvironmentStatus(False, "ManimGL is not installed in this Python environment.")
        return EnvironmentStatus(False, "This Python could not be started or checked.")
    if shutil.which("ffmpeg") is None:
        return EnvironmentStatus(False, f"ManimGL {version} found, but ffmpeg is not on PATH (needed to write MP4).", version)
    note = "" if version == SUPPORTED_MANIMGL else f" (tested with {SUPPORTED_MANIMGL})"
    return EnvironmentStatus(True, f"ManimGL {version} ready{note}", version)


def default_manim_python(project_root: Path) -> str:
    """The interpreter of ``.venv-manim`` next to the project, where the setup script puts it."""
    folder = "Scripts" if sys.platform == "win32" else "bin"
    name = "python.exe" if sys.platform == "win32" else "python"
    candidate = project_root / ".venv-manim" / folder / name
    return str(candidate) if candidate.exists() else ""
