"""
Centralized logging configuration for PiesPlanos using LogCentral.

Usage:
    from src.utils.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("message")

Log level controlled by LOGCENTRAL_LEVEL env var (DEBUG|INFO|WARNING|ERROR).
"""
from logcentral_client import get_logger as _lc_get_logger

_log = _lc_get_logger("piesplanos")


def get_logger(name: str):
    """Return a LogCentral logger bound to the given module name.

    Args:
        name: Module name (pass __name__). Used as extra context in log records.
    """
    return _log.bind(module=name)


def configure_logging():
    """No-op kept for backwards compatibility. LogCentral self-configures."""
    return _log
