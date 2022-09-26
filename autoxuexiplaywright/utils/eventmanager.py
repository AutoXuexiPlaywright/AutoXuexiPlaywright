from autoxuexiplaywright.defines import events

__all__ = ["find_event_by_id", "clean_callbacks"]

event_instances: list[events.Event] = [
    events.FinishedEvent(),
    events.QRUpdatedEvent(),
    events.ScoreUpdatedEvent(),
    events.StatusUpdatedEvent(),
    events.AnswerReuestedEvent()
]


def find_event_by_id(id: events.EventId) -> events.Event | None:
    for event_instance in event_instances:
        if event_instance.id == id:
            return event_instance
    return None


def clean_callbacks():
    for event_instance in event_instances:
        event_instance.clean_callback()
