from enum import Enum

from autoxuexiplaywright.defines.types import EventCallbackType

__all__ = ["EventId"]


class EventId(Enum):
    NONE = 0
    FINISHED = 1
    STATUS_UPDATED = 2
    QR_UPDATED = 3
    SCORE_UPDATED = 4
    ANSWER_REQUESTED = 5


class Event():
    def __init__(self) -> None:
        self.callbacks: list[EventCallbackType] = []
        self.id: EventId = EventId.NONE

    def add_callback(self, callback: EventCallbackType) -> None:
        self.callbacks.append(callback)

    def invoke(self, *args: ...) -> None:
        for callback in self.callbacks:
            callback(*args)

    def clean_callback(self) -> None:
        self.callbacks.clear()


class FinishedEvent(Event):
    def __init__(self) -> None:
        super().__init__()
        self.id = EventId.FINISHED


class StatusUpdatedEvent(Event):
    def __init__(self) -> None:
        super().__init__()
        self.id = EventId.STATUS_UPDATED


class QRUpdatedEvent(Event):
    def __init__(self) -> None:
        super().__init__()
        self.id = EventId.QR_UPDATED


class ScoreUpdatedEvent(Event):
    def __init__(self) -> None:
        super().__init__()
        self.id = EventId.SCORE_UPDATED


class AnswerReuestedEvent(Event):
    def __init__(self) -> None:
        super().__init__()
        self.id = EventId.ANSWER_REQUESTED
