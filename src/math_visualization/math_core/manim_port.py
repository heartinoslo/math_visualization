"""Small pieces ported from 3Blue1Brown's manim (ManimGL 1.7.2).

Only pure formulas and constants are copied, so the live renderer moves and
colours things exactly as an exported Manim scene would, without depending on
the manim package itself.

Source: https://github.com/3b1b/manim (manimlib/utils/rate_functions.py,
manimlib/utils/paths.py, manimlib/default_config.yml)

MIT License — Copyright (c) 2020-2023 3Blue1Brown LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

from collections.abc import Callable


# Rate functions (manimlib/utils/rate_functions.py) ---------------------------


def linear(t: float) -> float:
    return t


def smooth(t: float) -> float:
    # Zero first and second derivatives at t=0 and t=1.
    # Equivalent to bezier([0, 0, 0, 1, 1, 1])
    s = 1 - t
    return (t**3) * (10 * s * s + 5 * s * t + t * t)


RATE_FUNCTIONS: dict[str, Callable[[float], float]] = {"smooth": smooth, "linear": linear}
# Manim animations, ApplyMatrix included, use ``smooth`` unless told otherwise.
DEFAULT_RATE_FUNCTION = "smooth"


# Paths (manimlib/utils/paths.py) ----------------------------------------------


def straight_path(start: float, end: float, alpha: float) -> float:
    """``interpolate(start, end, alpha)``: the path ApplyMatrix moves every point along."""
    return start + (end - start) * alpha


# Colours (manimlib/default_config.yml) ------------------------------------------

BLUE_D = "#29ABCA"
BLUE_C = "#58C4DD"
TEAL_C = "#5CD0B3"
GREEN_C = "#83C167"
YELLOW_C = "#FFFF00"
GOLD_C = "#F0AC5F"
RED_C = "#FC6255"
MAROON_C = "#C55F73"
PURPLE_C = "#9A72AC"
PURPLE_A = "#CAA3E8"
PINK = "#D147BD"
ORANGE = "#FF862F"
GREY_C = "#888888"
GREY_B = "#BBBBBB"
GREY_A = "#DDDDDD"
WHITE = "#FFFFFF"
BACKGROUND = "#333333"

# 3Blue1Brown's linear-algebra conventions.
I_HAT_COLOR = GREEN_C
J_HAT_COLOR = RED_C
UNIT_SQUARE_COLOR = YELLOW_C
FOREGROUND_GRID_COLOR = BLUE_D
