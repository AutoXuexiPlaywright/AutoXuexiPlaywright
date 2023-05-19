from enum import Enum
from typing import Callable, Any


class EventID(Enum):
    NONE = 0
    FINISHED = 1
    STATUS_UPDATED = 2
    QR_UPDATED = 3
    SCORE_UPDATED = 4
    ANSWER_REQUESTED = 5

    @classmethod
    def __missing__(cls, value: object):
        return EventID.NONE


class Event(object):
    def __init__(self, id: EventID = EventID.NONE):
        self.callbacks: list[Callable[..., None]] = []
        self.id = id

    def add_callback(self, callback: Callable[..., None]):
        """Add a callback to the event

        Args:
            callback (Callable[..., None]): The callback function
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def invoke(self, *args: Any, **kwargs: Any):
        """Invoke the callbacks in the event

            **Note:** args and kwargs will be passed to the callbacks as parameter

        """
        for callback in self.callbacks:
            try:
                callback(*args, **kwargs)
            except:
                pass


class NoSuchEventException(Exception):
    def __init__(self, id: EventID) -> None:
        self.id = id
        super().__init__("No such event: %s" % id)


_events: list[Event] = [Event(id) for id in EventID if id != EventID.NONE]


def find_event_by_id(id: EventID) -> Event:
    """Find an event by the id given

    Args:
        id (EventID): The id

    Raises:
        NoSuchEventException: When no such event

    Returns:
        Event: The event
    """
    events = list(filter(lambda i: i.id == id, _events))
    if len(events) > 0:
        return events[0]
    raise NoSuchEventException(id)
