from logging import Handler, LogRecord
from PySide6.QtCore import Signal, SignalInstance, QObject, QWaitCondition, QMutex  # type: ignore

from autoxuexiplaywright.utils.start import start


class QHandler(Handler):
    def __init__(self, signal: SignalInstance) -> None:
        super().__init__()
        self.signal = signal

    def emit(self, record: LogRecord) -> None:
        self.signal.emit(self.format(record))


class SubProcess(QObject):
    job_finished_signal = Signal(str)
    update_status_signal = Signal(str)
    pause_thread_signal = Signal(tuple)
    qr_control_signal = Signal(bytes)
    update_score_signal = Signal(tuple)
    update_log_signal = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.st = QHandler(self.update_log_signal)
        self.wait = QWaitCondition()
        self.mutex = QMutex()

    def start(self) -> None:
        start(self.st)

    def pause(self, *args: ...):
        self.mutex.lock()
        self.pause_thread_signal.emit(args)
        self.wait.wait(self.mutex)
        self.mutex.unlock()


__all__ = ["SubProcess"]
