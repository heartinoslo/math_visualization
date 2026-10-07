"""Text formatting and parsing of numbers shown in editable fields."""

from __future__ import annotations

import math


def format_number(value: float, max_decimals: int = 4) -> str:
    """Short display text: at most ``max_decimals`` decimals, no trailing zeros, no ``-0``."""
    text = f"{value:.{max_decimals}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


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
