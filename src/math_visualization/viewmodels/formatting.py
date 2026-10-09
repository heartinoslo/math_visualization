"""Text formatting and parsing of numbers shown in editable fields."""

from __future__ import annotations

import math


def format_number(value: float, max_decimals: int = 4) -> str:
    """Short display text: at most ``max_decimals`` decimals, no trailing zeros, no ``-0``."""
    text = f"{value:.{max_decimals}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def format_quantity(value: float, digits: int = 4) -> str:
    """Read-only display of a computed value: fixed-point when readable, else scientific.

    Unlike :func:`format_number`, tiny but non-zero values such as a
    near-singular determinant never round to ``0``.
    """
    if math.isinf(value):
        return "∞"
    if value == 0.0 or 1e-3 <= abs(value) < 1e6:
        return format_number(value, digits)
    mantissa, exponent = f"{value:.{digits - 1}e}".split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}e{int(exponent)}"


def parse_number(text: str) -> float:
    """Parse user input such as ``"2"``, ``" -1.5 "`` or ``"−3"`` into a finite float."""
    cleaned = text.strip().replace("−", "-").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"{text.strip() or 'Empty input'!s} is not a number") from None
    if not math.isfinite(value):
        raise ValueError(f"{text.strip()} is not a finite number")
    return value
