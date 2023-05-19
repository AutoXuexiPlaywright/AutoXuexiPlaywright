from io import BytesIO
from PIL import Image
from queue import Queue
from logging import Handler
from qrcode import QRCode  # type: ignore
from pyzbar.pyzbar import decode  # type: ignore
# Relative imports
from .logger import init_logger
from .processors import start_processor
from .events import EventID, find_event_by_id
from .processors.common import ANSWER_CONNECTOR
from .languages import get_language_string


def _request_answer(tips: str, queue: Queue[list[str]]):
    queue.put(
        input(
            get_language_string("core-manual-enter-answer-required") %
            (ANSWER_CONNECTOR, tips)
        ).strip().split(ANSWER_CONNECTOR)
    )


def _print_qr(image: bytes):
    data = decode(Image.open(BytesIO(image)))[0]  # type: ignore
    qr = QRCode(box_size=4)  # type: ignore
    qr.add_data(data.data)  # type: ignore
    qr.print_tty()  # type: ignore


def register_callbacks():
    find_event_by_id(EventID.ANSWER_REQUESTED).add_callback(
        _request_answer)
    find_event_by_id(EventID.QR_UPDATED).add_callback(
        _print_qr)


def start(st: Handler | None = None):
    init_logger(st)
    start_processor()
