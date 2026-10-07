# Math Visualization

An interactive linear algebra visualization application built with PySide6, QML, Qt Quick, and Qt Quick 3D.

## Initial scope

- Vector visualization
- 2D coordinate systems
- 2×2 matrix transformations
- Interactive transformation animation
- Determinant and rank visualization

## Technology stack

- Python 3.12
- PySide6
- QML / Qt Quick
- Qt Quick 3D
- NumPy
- SciPy
- pytest

## Development environment

Create and activate a project-local virtual environment, then install the
package in editable mode together with the development tools:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

`requirements.txt` lists only the runtime dependencies; `requirements-lock.txt`
pins the exact versions last verified.

## Running

```powershell
python -m math_visualization   # or: math-visualization, or: python main.py
```

## Tests

```powershell
python -m pytest
```

Tests run offscreen. Qt Quick 3D cannot render on the offscreen platform, so
the pixel-level 3D rendering test is skipped there; on Linux it can be run
under a virtual display:

```bash
QT_QPA_PLATFORM=xcb xvfb-run -a python -m pytest
```

## License
This project is licensed under the GNU General Public License v3.0.
See the [LICENSE](LICENSE) file for details.