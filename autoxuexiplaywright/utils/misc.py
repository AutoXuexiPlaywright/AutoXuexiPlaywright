from os import putenv
from io import BytesIO
from qrcode import QRCode
from logging import (
    Handler, Formatter, StreamHandler, FileHandler, getLogger, INFO, DEBUG
)
from PIL import Image
from typing import Union
from pyzbar import pyzbar

from autoxuexiplaywright.defines.core import (
    APPID, LOGGING_FMT, LOGGING_DATETIME_FMT
)
from autoxuexiplaywright.defines.events import EventId
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.eventmanager import find_event_by_id


def init_logger(st: Handler = StreamHandler(), **kwargs) -> None:
    logger = getLogger(APPID)
    fmt = Formatter(fmt=LOGGING_FMT,
                    datefmt=LOGGING_DATETIME_FMT)
    level = DEBUG if kwargs.get("debug", False) else INFO
    fh = FileHandler(get_cache_path(
        APPID+".log"), "w", "utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    st.setLevel(level)
    st.setFormatter(fmt)
    if kwargs.get("debug", False):
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


def img2shell(img: bytes, **kwargs) -> None:
    if kwargs.get("gui", True):
        getLogger(APPID).info(get_lang(
            kwargs.get("lang", "zh-cn"), "ui-info-failed-to-print-qr"))
        find_event_by_id(EventId.QR_UPDATED).invoke(img)
    else:
        data: pyzbar.Decoded = pyzbar.decode(Image.open(BytesIO(img)))[0]
        qr = QRCode()
        qr.add_data(data.data.decode())
        qr.print_tty()


def start_backend(**kwargs) -> None:
    if kwargs.get("async", False):
        from autoxuexiplaywright.core.asyncprocessor import start
    else:
        from autoxuexiplaywright.core.syncprocessor import start
    start(**kwargs)
