"""Test if find_event_by_id is correct."""

import pytest
from autoxuexiplaywright.events import EventID
from autoxuexiplaywright.events import NoSuchEventException
from autoxuexiplaywright.events import find_event_by_id


def test_find_event_by_id():
    """Check if find_event_by_id works."""
    for _id in EventID:
        if _id == EventID.NONE:
            with pytest.raises(NoSuchEventException):
                _ = find_event_by_id(_id)
        else:
            _ = find_event_by_id(_id)
    with pytest.raises(NoSuchEventException):
        _ = find_event_by_id(EventID(-1))
