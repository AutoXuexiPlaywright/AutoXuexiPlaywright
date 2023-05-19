from logging import Handler, LogRecord
from PySide6.QtCore import Signal, SignalInstance, QObject, QWaitCondition, QMutex
# Relative imports
from ..events import EventID, find_event_by_id
from ..logger import init_logger
from ..processors import start_processor


class _QHandler(Handler):
    def __init__(self, signal: SignalInstance):
        super().__init__()
        self.signal = signal

    def emit(self, record: LogRecord):
        self.signal.emit(self.format(record))


class SubProcess(QObject):
    jobFinishedSignal = Signal(str)
    updateStatusSignal = Signal(str)
    pauseThreadSignal = Signal(tuple)
    qrControlSignal = Signal(bytes)
    updateScoreSignal = Signal(tuple)
    updateLogSignal = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.st = _QHandler(self.updateLogSignal)
        self.wait = QWaitCondition()
        self.mutex = QMutex()
        find_event_by_id(EventID.FINISHED).add_callback(
            self.jobFinishedSignal.emit)
        find_event_by_id(EventID.STATUS_UPDATED).add_callback(
            self.updateStatusSignal.emit)
        find_event_by_id(EventID.QR_UPDATED).add_callback(
            self.qrControlSignal.emit)
        find_event_by_id(EventID.SCORE_UPDATED).add_callback(
            self.updateScoreSignal.emit)
        find_event_by_id(EventID.ANSWER_REQUESTED).add_callback(self.pause)

    def start(self):
        init_logger(self.st)
        start_processor()

    def pause(self, *args: ...):
        self.mutex.lock()
        self.pauseThreadSignal.emit(args)
        self.wait.wait(self.mutex)
        self.mutex.unlock()
