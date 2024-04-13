"""Classes and functions for Event system."""

from enum import Enum
from typing import Any
from typing import Callable
from contextlib import suppress
from typing_extensions import override


class EventID(Enum):
    """ID of all events."""
    NONE = 0
    FINISHED = 1
    STATUS_UPDATED = 2
    QR_UPDATED = 3
    SCORE_UPDATED = 4
    ANSWER_REQUESTED = 5

    @classmethod
    @override
    def _missing_(cls, value: object):
        """Triggered when EventID(...) is called and nothing matched."""
        return EventID.NONE


class Event(object):
    """Event will be triggered during execution."""
    def __init__(self, _id: EventID = EventID.NONE):
        """Create an Event instance.

        Args:
            _id(EventID): The ID of event, defaults to EventID.NONE
        """
        self.callbacks: list[Callable[..., None]] = []
        self.id_ = _id

    def add_callback(self, callback: Callable[..., None]):
        """Add a callback to the event.

        Args:
            callback (Callable[..., None]): The callback function
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def invoke(self, *args: Any, **kwargs: Any):
        """Invoke the callbacks in the event.

        **Note:** args and kwargs will be passed to the callbacks as parameter
                  Each callback will block the thread.

        """
        for callback in self.callbacks:
            with suppress(Exception):
                callback(*args, **kwargs)


class NoSuchEventException(Exception):
    """Exception shows that no event is found."""
    def __init__(self, _id: EventID) -> None:
        """Create a NoSuchEventException instance.

        Args:
            _id(EventID): The event id.
        """
        self._id = _id
        super().__init__("No such event: %s" % _id)


_events: list[Event] = [Event(_id) for _id in EventID if _id != EventID.NONE]


def find_event_by_id(_id: EventID) -> Event:
    """Find an event by the id given.

    Args:
        _id (EventID): The id

    Raises:
        NoSuchEventException: When no such event

    Returns:
        Event: The event
    """
    for event in _events:
        if event.id_ == _id:
            return event
    raise NoSuchEventException(_id)
