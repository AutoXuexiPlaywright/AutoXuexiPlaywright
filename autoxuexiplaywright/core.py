"""Main module when runs in headless mode."""

from io import BytesIO
from PIL import Image
from queue import Queue
from qrcode import QRCode  # type: ignore
from .events import EventID
from .events import find_event_by_id

# Relative imports
from .logger import init_logger
from logging import Handler
from .languages import get_language_string
from .processors import start_processor
from pyzbar.pyzbar import decode  # type: ignore
from .processors.common import ANSWER_CONNECTOR


def _request_answer(tips: str, queue: Queue[list[str]]):
    queue.put(
        input(
            get_language_string("core-manual-enter-answer-required") % (ANSWER_CONNECTOR, tips),
        )
        .strip()
        .split(ANSWER_CONNECTOR),
    )


def _print_qr(image: bytes):
    data = decode(Image.open(BytesIO(image)))[0]  # type: ignore
    qr = QRCode(box_size=4)  # type: ignore
    qr.add_data(data.data)  # type: ignore
    qr.print_tty()  # type: ignore


def register_callbacks():
    """Register required callbacks."""
    find_event_by_id(EventID.ANSWER_REQUESTED).add_callback(_request_answer)
    find_event_by_id(EventID.QR_UPDATED).add_callback(_print_qr)


def start(st: Handler | None = None):
    """Main entrance of headless mode.

    Args:
        st(Handler|None): log handler, defaults to None for StreamHandler
    """
    init_logger(st)
    start_processor()
