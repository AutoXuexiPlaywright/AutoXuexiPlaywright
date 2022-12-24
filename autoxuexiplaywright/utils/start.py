from logging import Handler

from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.utils.logger import init_logger


def start(st: Handler | None = None) -> None:
    init_logger(st)
    if Config.get_instance().async_mode:
        from autoxuexiplaywright.asyncprocessor import start
    else:
        from autoxuexiplaywright.syncprocessor import start
    start()
