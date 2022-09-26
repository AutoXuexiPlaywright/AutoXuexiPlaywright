import logging
from autoxuexiplaywright.utils import misc, config
from qtpy.QtCore import Signal, SignalInstance, QObject, QWaitCondition, QMutex


__all__ = ["SubProcess"]


class QHandler(logging.Handler):
    def __init__(self, signal: SignalInstance, **kwargs) -> None:
        super().__init__(**kwargs)
        self.signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        self.signal.emit(self.format(record))


class SubProcess(QObject):
    job_finished_signal = Signal(str)
    update_status_signal = Signal(str)
    pause_thread_signal = Signal(tuple)
    qr_control_signal = Signal(bytes)
    update_score_signal = Signal(tuple)
    update_log_signal = Signal(str)

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.st = QHandler(self.update_log_signal)
        self.wait = QWaitCondition()
        self.mutex = QMutex()
        self.kwargs = kwargs

    def start(self) -> None:
        self.kwargs.update(**config.get_runtime_config())
        misc.init_logger(self.st, **self.kwargs)
        misc.start_backend(**self.kwargs)

    def pause(self, *args):
        self.mutex.lock()
        self.pause_thread_signal.emit(args)
        self.wait.wait(self.mutex)
        self.mutex.unlock()
