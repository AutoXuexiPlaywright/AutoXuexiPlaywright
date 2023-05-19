from autoxuexiplaywright.events import find_event_by_id, EventID, NoSuchEventException


def test_find_event_by_id():
    for id in EventID:
        if id == EventID.NONE:
            try:
                find_event_by_id(id)
            except NoSuchEventException:
                pass
            else:
                raise Exception
        else:
            find_event_by_id(id)
    setattr(EventID, "TEST", -1)
    try:
        find_event_by_id(getattr(EventID, "TEST"))
    except NoSuchEventException:
        pass
    else:
        raise Exception
    finally:
        delattr(EventID, "TEST")
