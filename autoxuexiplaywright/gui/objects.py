import sys
import queue
import logging
from autoxuexiplaywright.utils import misc, config
from qtpy.QtCore import Signal, SignalInstance, QObject, QWaitCondition, QMutex  # type: ignore


__all__ = ["SubProcess"]


class QHandler(logging.Handler):
    def __init__(self, signal: SignalInstance, **kwargs) -> None:
        super().__init__(**kwargs)
        self.signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        self.signal.emit(self.format(record))


class SubProcess(QObject):
    job_finished_signal = Signal()
    update_status_signal = Signal(str)
    pause_thread_signal = Signal(str)
    qr_control_signal = Signal(bytes)
    update_score_signal = Signal(tuple)
    update_log_signal = Signal(str)

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.st = QHandler(self.update_log_signal)  # type: ignore
        self.answer_queue = queue.Queue(1)
        self.wait = QWaitCondition()
        self.mutex = QMutex() # type: ignore
        self.kwargs = kwargs

    def start(self) -> None:
        self.kwargs.update(**config.get_runtime_config())
        misc.start_backend(*sys.argv, wait=self.wait, mutex=self.mutex,
                           st=self.st, answer_queue=self.answer_queue, job_finish_signal=self.job_finished_signal,
                           update_status_signal=self.update_status_signal, pause_thread_signal=self.pause_thread_signal,
                           qr_control_signal=self.qr_control_signal, update_score_signal=self.update_score_signal, **self.kwargs)
