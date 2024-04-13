"""Classes and functions for logging."""

from os import environ

# Relative imports
from .config import get_runtime_config
from logging import INFO
from logging import DEBUG
from logging import Handler
from logging import Formatter
from logging import FileHandler
from logging import StreamHandler
from logging import getLogger
from .defines import APPNAME
from .storage import get_cache_path


_LOGGING_STRING_FMT = "%(asctime)s-%(levelname)s-%(message)s"
_LOGGING_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_logger = getLogger(APPNAME)
_context = {"init": False}


def debug(msg: object) -> None:
    """Generate a debug message.

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.debug(msg)
    return None


def info(msg: object) -> None:
    """Generate a info message.

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.info(msg)
    return None


def warning(msg: object) -> None:
    """Generate a warning message.

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.warning(msg)
    return None


def error(msg: object) -> None:
    """Generate an error message.

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.error(msg)
    return None


def init_logger(st: Handler | None = None):
    """Init the logger.

    Args:
        st (Handler | None, optional): Any Handler for printing log records. Defaults to None.
    """
    if not _context["init"]:
        if st is None:
            st = StreamHandler()
        if get_runtime_config().debug:
            level = DEBUG
            environ["DEBUG"] = "pw:api"
        else:
            level = INFO
            environ["DEBUG"] = ""
        fh = FileHandler(get_cache_path(APPNAME + ".log"), "w", "utf-8")
        fm = Formatter(_LOGGING_STRING_FMT, _LOGGING_DATE_FMT)
        _logger.setLevel(level)
        st.setFormatter(fm)
        st.setLevel(level)
        fh.setFormatter(fm)
        fh.setLevel(level)
        for handler in _logger.handlers:
            _logger.removeHandler(handler)
        _logger.addHandler(st)
        _logger.addHandler(fh)
        _context["init"] = True
