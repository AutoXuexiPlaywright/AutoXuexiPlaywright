from autoxuexiplaywright.defines.events import (
    Event, EventId, FinishedEvent, QRUpdatedEvent, ScoreUpdatedEvent, StatusUpdatedEvent, AnswerReuestedEvent
)


event_instances: list[Event] = [
    FinishedEvent(),
    QRUpdatedEvent(),
    ScoreUpdatedEvent(),
    StatusUpdatedEvent(),
    AnswerReuestedEvent()
]


def find_event_by_id(id: EventId) -> Event:
    for event_instance in event_instances:
        if event_instance.id == id:
            return event_instance
    raise NoSuchEventException(id)


def clean_callbacks():
    for event_instance in event_instances:
        event_instance.clean_callback()


class NoSuchEventException(Exception):
    """Raises when no such event

    Args:
        Exception (EventId): the event ID
    """

    def __init__(self, id: EventId):
        super().__init__("No Such Event:{0}".format(id))


__all__ = ["find_event_by_id", "clean_callbacks"]
