import os
import io
import qrcode
import logging
from PIL import Image
from typing import Union
from pyzbar import pyzbar
from autoxuexiplaywright.defines import core, events
from autoxuexiplaywright.utils import lang, storage, eventmanager


def init_logger(*args, **kwargs) -> None:
    logger = logging.getLogger(core.APPID)
    fmt = logging.Formatter(fmt=core.LOGGING_FMT,
                            datefmt=core.LOGGING_DATETIME_FMT)
    fh = logging.FileHandler(storage.get_cache_path(
        core.APPID+".log"), "w", "utf-8")
    fh.setLevel(logging.DEBUG if kwargs.get("debug", False) else logging.INFO)
    fh.setFormatter(fmt)
    st = kwargs.get("st", logging.StreamHandler())
    st.setLevel(logging.DEBUG if kwargs.get("debug", False) else logging.INFO)
    st.setFormatter(fmt)
    if kwargs.get("debug", False):
        os.putenv("DEBUG", "pw:api")
    logger.setLevel(logging.DEBUG if kwargs.get(
        "debug", False) else logging.INFO)
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
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "ui-info-failed-to-print-qr"))
        eventmanager.find_event_by_id(events.EventId.QR_UPDATED).invoke(img)
    else:
        data: pyzbar.Decoded = pyzbar.decode(Image.open(io.BytesIO(img)))[0]
        qr = qrcode.QRCode()
        qr.add_data(data.data.decode())
        qr.print_tty()


def start_backend(*args, **kwargs) -> None:
    if kwargs.get("async", False):
        from autoxuexiplaywright.core import asyncprocessor as processor
    else:
        from autoxuexiplaywright.core import syncprocessor as processor
    processor.start(*args, **kwargs)
