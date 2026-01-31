"""Logging configuration for PDFResolve."""

import logging
import sys
from typing import Literal


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    format_string: str | None = None,
) -> logging.Logger:
    """Set up logging for PDFResolve.

    Args:
        level: Logging level
        format_string: Custom format string (optional)

    Returns:
        Configured logger
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logger
    logger = logging.getLogger("pdfresolve")
    logger.setLevel(getattr(logging, level))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(getattr(logging, level))

    # Create formatter
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger(name: str = "pdfresolve") -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (will be prefixed with 'pdfresolve.')

    Returns:
        Logger instance
    """
    if not name.startswith("pdfresolve"):
        name = f"pdfresolve.{name}"
    return logging.getLogger(name)
