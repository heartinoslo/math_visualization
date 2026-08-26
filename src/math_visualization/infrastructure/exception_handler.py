"""Global uncaught-exception handling for application startup and runtime."""

from __future__ import annotations

import logging
import sys
from types import TracebackType
from typing import Callable

from math_visualization.infrastructure.logging_config import (
    APPLICATION_LOGGER_NAME,
)


ExceptionHook = Callable[[type[BaseException], BaseException, TracebackType | None], None]


def handle_uncaught_exception(
    exception_type: type[BaseException],
    exception: BaseException,
    traceback: TracebackType | None,
    *,
    logger: logging.Logger | None = None,
) -> None:
    """Log an uncaught exception with its original traceback."""
    active_logger = logger or logging.getLogger(APPLICATION_LOGGER_NAME)
    active_logger.critical(
        "Unhandled Python exception",
        exc_info=(exception_type, exception, traceback),
    )


def install_exception_handler(logger: logging.Logger | None = None) -> ExceptionHook:
    """Install and return the previous process-wide Python exception hook."""
    previous_hook = sys.excepthook

    def exception_hook(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        if issubclass(exception_type, KeyboardInterrupt):
            previous_hook(exception_type, exception, traceback)
            return
        handle_uncaught_exception(
            exception_type,
            exception,
            traceback,
            logger=logger,
        )

    sys.excepthook = exception_hook
    return previous_hook
