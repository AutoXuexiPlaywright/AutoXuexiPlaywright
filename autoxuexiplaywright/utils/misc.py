from os import putenv
from io import BytesIO
from qrcode import QRCode # type: ignore
from logging import (
    Handler, Formatter, StreamHandler, FileHandler, getLogger, INFO, DEBUG
)
from PIL import Image
from typing import Union
from pyzbar.pyzbar import Decoded, decode # type: ignore

from autoxuexiplaywright.defines.core import (
    APPID, LOGGING_FMT, LOGGING_DATETIME_FMT
)
from autoxuexiplaywright.defines.events import EventId
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.eventmanager import find_event_by_id
from autoxuexiplaywright.utils.config import Config


def init_logger(st: Handler = StreamHandler()) -> None:
    logger = getLogger(APPID)
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
        putenv("DEBUG", "pw:api")
    logger.setLevel(level)
    for handler in logger.handlers:
        logger.removeHandler(handler)
    logger.addHandler(st)
    logger.addHandler(fh)


def to_str(obj: Union[str, None]) -> str:
    if obj is None:
        return ""
    return obj


def img2shell(img: bytes, ) -> None:
    config = Config.get_instance()
    if config.gui:
        getLogger(APPID).info(get_lang(
            config.lang, "ui-info-failed-to-print-qr"))
        find_event_by_id(EventId.QR_UPDATED).invoke(img)
    else:
        datas: list[Decoded] = decode(Image.open(BytesIO(img)))[0]
        qr = QRCode()
        qr.add_data(datas[0].data) # type: ignore
        qr.print_tty() # type: ignore


def start_backend() -> None:
    if Config.get_instance().async_mode:
        from autoxuexiplaywright.core.asyncprocessor import start
    else:
        from autoxuexiplaywright.core.syncprocessor import start
    start()


def start(st: Handler | None = None) -> None:
    if st is not None:
        init_logger(st)
    else:
        init_logger()
    start_backend()
