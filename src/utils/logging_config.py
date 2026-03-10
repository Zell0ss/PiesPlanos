"""
Centralized logging configuration for the game
Supports LOG_LEVEL environment variable: DEBUG, INFO, WARNING, ERROR, NONE
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()


def configure_logging():
    """
    Configure logging based on LOG_LEVEL environment variable.

    Supported values:
    - DEBUG: Show all debug information
    - INFO: Show informational messages (default)
    - WARNING: Show only warnings and errors
    - ERROR: Show only errors
    - NONE: Disable all logging

    Returns:
        logging.Logger: Configured root logger
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Map string to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "NONE": logging.CRITICAL + 1,  # Higher than CRITICAL to disable all
    }

    log_level = level_map.get(log_level_str, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s:%(name)s:%(message)s",
        force=True,  # Override any existing configuration
    )

    # If NONE, disable all loggers
    if log_level_str == "NONE":
        logging.disable(logging.CRITICAL)

    logger = logging.getLogger(__name__)

    if log_level_str != "NONE":
        logger.debug(f"Logging configured at level: {log_level_str}")

    return logging.getLogger()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the configured log level.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(name)
