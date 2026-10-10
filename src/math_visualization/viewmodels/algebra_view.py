"""What the Algebra view shows for an operation at a given playback progress.

The operation is laid out as terms (matrices, operators, numbers). Playback
walks through the derivation one step per segment: the current step's
entries are highlighted, and each result entry appears once it is computed.
"""

from __future__ import annotations

import math

from math_visualization.math_core.matrix_algebra import Derivation, Matrix, OperationKind, number


def step_at(progress: float, step_count: int) -> int:
    """The step shown at ``progress`` ∈ [0, 1]: segment k covers [k/n, (k+1)/n)."""
    if step_count <= 0:
        return 0
    return min(step_count - 1, max(0, math.floor(progress * step_count)))


def _matrix_term(role: str, name: str, matrix: Matrix, states: dict, hidden: set | None = None) -> dict:
    size = matrix.size
    cells = []
    for row in range(size):
        for column in range(size):
            state = states.get((row, column), "normal")
            hide = hidden is not None and (row, column) in hidden
            cells.append({"text": "?" if hide else number(matrix.entry(row, column)), "state": "hidden" if hide else state})
    return {"type": "matrix", "role": role, "name": name, "size": size, "cells": cells}


def _operator(text: str) -> dict:
    return {"type": "operator", "text": text}


def matrix_view(name: str, matrix: Matrix) -> dict:
    """A single matrix, when no operation is selected."""
    return {
        "terms": [_operator(f"{name} ="), _matrix_term("left", name, matrix, {})],
        "title": f"{name}  ({matrix.size}×{matrix.size})",
        "formula": "",
        "history": [],
        "step": 0,
        "stepCount": 0,
    }


def operation_view(derivation: Derivation, progress: float) -> dict:
    steps = derivation.steps
    current = step_at(progress, len(steps))
    step = steps[current]
    names = derivation.operand_names
    kind = derivation.kind

    # Highlight states per role for the current step.
    states: dict[str, dict] = {"left": {}, "right": {}, "result": {}}
    for mark in step.marks:
        states[mark.role][(mark.row, mark.column)] = mark.kind
    if kind is OperationKind.DETERMINANT and derivation.size == 3 and current < len(steps) - 1:
        # Cells outside the current cofactor term step back.
        size = derivation.size
        for row in range(size):
            for column in range(size):
                states["left"].setdefault((row, column), "dim")

    revealed = {s.target for s in steps[: current + 1] if s.target is not None}
    # A determinant's value appears with its last step (the sum).
    finished = progress >= 1.0 or (kind is OperationKind.DETERMINANT and current == len(steps) - 1)
    if progress >= 1.0:
        revealed = {s.target for s in steps if s.target is not None}

    left = _matrix_term("left", names[0], derivation.operands[0], states["left"])
    terms: list[dict]
    if kind is OperationKind.DETERMINANT:
        value = number(derivation.result) if finished else "?"
        terms = [_operator("det"), left, _operator("="), {"type": "number", "text": value}]
    else:
        result = derivation.result
        size = result.size
        hidden = {(r, c) for r in range(size) for c in range(size)} - revealed
        result_term = _matrix_term("result", derivation.result_name, result, states["result"], hidden)
        if kind is OperationKind.SCALE:
            terms = [{"type": "number", "text": number(derivation.scalar)}, _operator("·"), left]
        elif kind is OperationKind.TRANSPOSE:
            left["superscript"] = "T"
            terms = [left]
        else:
            symbol = {OperationKind.ADD: "+", OperationKind.SUBTRACT: "−", OperationKind.MULTIPLY: "·"}[kind]
            right = _matrix_term("right", names[1], derivation.operands[1], states["right"])
            terms = [left, _operator(symbol), right]
        terms += [_operator("="), result_term]

    return {
        "terms": terms,
        "title": derivation.title,
        "formula": step.formula,
        "history": [s.formula for s in steps[:current]],
        "step": current + 1,
        "stepCount": len(steps),
    }
