from os import environ
from logging import Formatter, Handler, StreamHandler, FileHandler, getLogger, DEBUG, INFO
# Relative imports
from .config import get_runtime_config
from .defines import APPNAME
from .storage import get_cache_path


_LOGGING_STRING_FMT = "%(asctime)s-%(levelname)s-%(message)s"
_LOGGING_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_logger = getLogger(APPNAME)
_context = {"init": False}


def debug(msg: object):
    """Generate a debug message

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.debug(msg)


def info(msg: object):
    """Generate a info message

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.info(msg)


def warning(msg: object):
    """Generate a warning message

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.warning(msg)


def error(msg: object):
    """Generate an error message

    Args:
        msg (object): The message

    """
    if _context["init"]:
        return _logger.error(msg)


def init_logger(st: Handler | None = None):
    """Init the logger

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
        fh = FileHandler(get_cache_path(APPNAME+".log"), "w", "utf-8")
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
