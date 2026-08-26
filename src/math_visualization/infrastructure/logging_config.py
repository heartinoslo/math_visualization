"""Central logging configuration for the application."""

from __future__ import annotations

import logging


APPLICATION_LOGGER_NAME = "math_visualization"
_HANDLER_MARKER = "_math_visualization_console_handler"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Return the application logger with one predictable console handler.

    Repeated calls intentionally reuse the handler so tests and embedded startup
    paths do not produce duplicate messages.
    """
    logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not any(getattr(handler, _HANDLER_MARKER, False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        setattr(handler, _HANDLER_MARKER, True)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger
