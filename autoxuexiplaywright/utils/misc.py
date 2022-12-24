
from io import BytesIO
from qrcode import QRCode  # type: ignore
from PIL import Image
from pyzbar.pyzbar import Decoded, decode  # type: ignore

from autoxuexiplaywright.defines.events import EventId
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.eventmanager import find_event_by_id
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.utils.logger import logger


def to_str(obj: str | None) -> str:
    return "" if obj is None else obj


def img2shell(img: bytes) -> None:
    config = Config.get_instance()
    if config.gui:
        logger.info(get_lang(
            config.lang, "ui-info-failed-to-print-qr"))
        find_event_by_id(EventId.QR_UPDATED).invoke(img)
    else:
        data: Decoded = decode(Image.open(BytesIO(img)))[0]
        qr = QRCode(box_size=4)
        qr.add_data(data.data)  # type: ignore
        qr.print_tty()  # type: ignore
