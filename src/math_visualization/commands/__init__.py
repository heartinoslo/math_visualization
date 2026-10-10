"""Undoable document edits. Every change to scene objects goes through here."""

from math_visualization.commands.command import Command
from math_visualization.commands.command_manager import CommandManager
from math_visualization.commands.matrix_commands import (
    MATRIX_COMMANDS,
    AddMatrixCommand,
    RemoveMatrixCommand,
    UpdateMatrixCommand,
)
from math_visualization.commands.operation_commands import (
    OPERATION_COMMANDS,
    AddOperationCommand,
    RemoveOperationCommand,
)
from math_visualization.commands.vector_commands import (
    AddVectorCommand,
    RemoveVectorCommand,
    UpdateVectorCommand,
)

__all__ = [
    "MATRIX_COMMANDS",
    "OPERATION_COMMANDS",
    "AddMatrixCommand",
    "AddOperationCommand",
    "AddVectorCommand",
    "Command",
    "CommandManager",
    "RemoveMatrixCommand",
    "RemoveOperationCommand",
    "RemoveVectorCommand",
    "UpdateMatrixCommand",
    "UpdateVectorCommand",
]
