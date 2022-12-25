from os import environ
from logging import getLogger, FileHandler, Handler, StreamHandler, Formatter, DEBUG, INFO

from autoxuexiplaywright.defines.core import LOGGING_FMT, LOGGING_DATETIME_FMT, APPID
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.config import Config

logger = getLogger(APPID)


def init_logger(st: Handler | None = None) -> None:
    if st is None:
        st = StreamHandler()
    fmt = Formatter(fmt=LOGGING_FMT,
                    datefmt=LOGGING_DATETIME_FMT)
    debug = Config.get_instance().debug
    level = DEBUG if debug else INFO
    fh = FileHandler(get_cache_path(
        APPID+".log"), "w", "utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    st.setLevel(level)
    st.setFormatter(fmt)
    if debug:
        environ["DEBUG"] = "pw:api"
    logger.setLevel(level)
    for handler in logger.handlers:
        logger.removeHandler(handler)
    logger.addHandler(st)
    logger.addHandler(fh)
