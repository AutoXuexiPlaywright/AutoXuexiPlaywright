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


def find_event_by_id(id: EventId) -> Event | None:
    for event_instance in event_instances:
        if event_instance.id == id:
            return event_instance
    return None


def clean_callbacks():
    for event_instance in event_instances:
        event_instance.clean_callback()


__all__ = ["find_event_by_id", "clean_callbacks"]
