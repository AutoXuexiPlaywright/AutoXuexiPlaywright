"""Objects required in gui mode."""

from logging import Handler
from logging import LogRecord

# Relative imports
from ..events import EventID
from ..events import find_event_by_id
from ..logger import init_logger
from ..processors import start_processor
from PySide6.QtCore import QMutex
from PySide6.QtCore import Signal
from PySide6.QtCore import QObject
from PySide6.QtCore import QWaitCondition
from PySide6.QtCore import SignalInstance


class _QHandler(Handler):
    def __init__(self, signal: SignalInstance):
        super().__init__()
        self.signal = signal

    def emit(self, record: LogRecord):
        self.signal.emit(self.format(record))


class SubProcess(QObject):
    """QObject which will run in subprocess."""

    jobFinishedSignal = Signal(str)
    updateStatusSignal = Signal(str)
    pauseThreadSignal = Signal(tuple)
    qrControlSignal = Signal(bytes)
    updateScoreSignal = Signal(tuple)
    updateLogSignal = Signal(str)

    def __init__(self, parent: QObject | None = None):
        """Create a SubProcess instance.

        Args:
            parent(QObject|None): the parent QObject, defaults to None
        """
        super().__init__(parent)
        self.st = _QHandler(self.updateLogSignal)
        self.wait = QWaitCondition()
        self.mutex = QMutex()
        find_event_by_id(EventID.FINISHED).add_callback(self.jobFinishedSignal.emit)
        find_event_by_id(EventID.STATUS_UPDATED).add_callback(self.updateStatusSignal.emit)
        find_event_by_id(EventID.QR_UPDATED).add_callback(self.qrControlSignal.emit)
        find_event_by_id(EventID.SCORE_UPDATED).add_callback(self.updateScoreSignal.emit)
        find_event_by_id(EventID.ANSWER_REQUESTED).add_callback(self.pause)

    def start(self):
        """Start the process's work."""
        init_logger(self.st)
        start_processor()

    def pause(self, *args: ...):
        """Pause the process's work.

        Args:
            *args(Any): arguments passed to pauseThreadSignal
        """
        self.mutex.lock()
        self.pauseThreadSignal.emit(args)
        self.wait.wait(self.mutex)
        self.mutex.unlock()
