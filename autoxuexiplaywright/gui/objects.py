import sys
import logging
from autoxuexiplaywright.defines import events
from autoxuexiplaywright.utils import misc, config, eventmanager
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

    def register_callbacks(self):
        eventmanager.clean_callbacks()
        eventmanager.find_event_by_id(events.EventId.FINISHED).add_callback(
            self.job_finished_signal.emit)
        eventmanager.find_event_by_id(events.EventId.STATUS_UPDATED).add_callback(
            self.update_status_signal.emit)
        eventmanager.find_event_by_id(events.EventId.QR_UPDATED).add_callback(
            self.qr_control_signal.emit)
        eventmanager.find_event_by_id(events.EventId.SCORE_UPDATED).add_callback(
            self.update_score_signal.emit)
        eventmanager.find_event_by_id(events.EventId.ANSWER_REQUESTED).add_callback(
            self.on_answer_requested)

    def start(self) -> None:
        self.kwargs.update(**config.get_runtime_config())
        self.register_callbacks()
        misc.init_logger(self.st, **self.kwargs)
        misc.start_backend(*sys.argv, **self.kwargs)

    def on_answer_requested(self, *args):
        self.mutex.lock()
        self.pause_thread_signal.emit(args)
        self.wait.wait(self.mutex)
        self.mutex.unlock()
