"""Tests for Stage 0 infrastructure helpers."""

from __future__ import annotations

import logging
from unittest.mock import Mock

from math_visualization.infrastructure.exception_handler import handle_uncaught_exception
from math_visualization.infrastructure.logging_config import configure_logging


def test_logging_configuration_reuses_its_handler() -> None:
    logger = configure_logging()
    handler_count = len(logger.handlers)

    configured_again = configure_logging()

    assert configured_again is logger
    assert len(logger.handlers) == handler_count
    assert handler_count >= 1


def test_uncaught_exception_is_logged() -> None:
    logger = Mock(spec=logging.Logger)
    error = RuntimeError("test exception")

    try:
        raise error
    except RuntimeError as caught_error:
        handle_uncaught_exception(
            type(caught_error),
            caught_error,
            caught_error.__traceback__,
            logger=logger,
        )

    logger.critical.assert_called_once()
    assert logger.critical.call_args.args == ("Unhandled Python exception",)
    assert logger.critical.call_args.kwargs["exc_info"][1] is error
