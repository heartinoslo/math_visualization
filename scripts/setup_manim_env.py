"""Create the separate ManimGL environment used for video export.

Run it with the Python you want the environment to use (3.10–3.12):

    python scripts/setup_manim_env.py

It creates ``.venv-manim`` next to the project and installs the packages in
``requirements-manim.txt``. The application finds that environment by
itself; you can also choose another one in File → Export Video.
ManimGL writes MP4 through ffmpeg, which must be on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".venv-manim"
REQUIREMENTS = ROOT / "requirements-manim.txt"


def environment_python() -> Path:
    if sys.platform == "win32":
        return TARGET / "Scripts" / "python.exe"
    return TARGET / "bin" / "python"


def main() -> int:
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        print(f"ManimGL 1.7.2 needs Python 3.10–3.12; this is {sys.version.split()[0]}.")
        return 1
    if not environment_python().exists():
        print(f"Creating {TARGET} …")
        venv.EnvBuilder(with_pip=True).create(TARGET)
    python = str(environment_python())
    print("Installing ManimGL (this downloads about 250 MB the first time) …")
    subprocess.run([python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python, "-m", "pip", "install", "-r", str(REQUIREMENTS)], check=True)
    version = subprocess.run(
        [python, "-c", "import importlib.metadata as m; print(m.version('manimgl'))"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    print(f"ManimGL {version} is installed in {TARGET}.")
    if shutil.which("ffmpeg") is None:
        print(
            "ffmpeg was not found on PATH. Install it before exporting, for example:\n"
            "  Windows: winget install Gyan.FFmpeg   (then open a new terminal)\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   sudo apt install ffmpeg"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
