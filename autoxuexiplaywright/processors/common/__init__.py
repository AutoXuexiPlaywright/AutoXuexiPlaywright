"""Common objects for async and sync apis."""

from re import compile
from abc import ABC
from abc import abstractmethod
from enum import Enum


class TaskStatus(Enum):
    """Status of task."""

    UNKNOWN = 0
    READY = 1
    SUCCESS = 2
    FAILED = 3
    SKIPPED = 4


class AbstractBaseTask(ABC):
    """Common parts of Task in sync and async apis."""

    status = TaskStatus.UNKNOWN

    @property
    @abstractmethod
    def requires(self) -> list[str]:
        """What does this task requires."""
        return []

    @property
    @abstractmethod
    def handles(self) -> list[str]:
        """What does this task can do."""
        return []


WAIT_PAGE_SECS = 300
RETRY_TIMES = 3
CHECK_ELEMENT_TIMEOUT_SECS = 5
WAIT_RESULT_SECS = CHECK_ELEMENT_TIMEOUT_SECS
WAIT_CHOICE_SECS = CHECK_ELEMENT_TIMEOUT_SECS
ANSWER_SLEEP_MIN_SECS = 2.0
ANSWER_SLEEP_MAX_SECS = 5.0
READ_TIME_SECS = 60
READ_SLEEPS_MIN_SECS = 2.0
READ_SLEEPS_MAX_SECS = 5.0

VIDEO_REQUEST_REGEX = compile("https://.+.(m3u8|mp4)")

ANSWER_CONNECTOR = "#"

cache: set[str] = set()
tasks_to_be_done: list[str] = []
scores: list[int] = [-1, -1]

TaskQueue = list[str]

_known_tasks: list[AbstractBaseTask] = []


def _is_task_registered(task_type: type[AbstractBaseTask]) -> bool:
    return any(isinstance(task, task_type) for task in _known_tasks)


def get_task_by_task_title(task_title: str) -> AbstractBaseTask | None:
    """Get task by task title.

    Args:
        task_title (str): The title of task on status page

    Returns:
        AbstractBaseTask | None: The task instance or None if not found
    """
    for task in _known_tasks:
        if task_title in task.handles:
            return task
    return None


def register_tasks(*tasks: type[AbstractBaseTask]) -> bool:
    """Register all tasks given.

    This will make them available

    Returns:
        bool: If all tasks are registered successfully
    """
    results: list[bool] = []
    for task in tasks:
        if _is_task_registered(task):
            results.append(False)
        else:
            _known_tasks.append(task())
            results.append(True)
    return all(results)


def clean_tasks():
    """Remove all the registered tasks."""
    _known_tasks.clear()


def set_task_status_by_task_title(task_title: str, status: TaskStatus) -> bool:
    """Set task status by task title.

    Args:
        task_title (str): The title of task on status page
        status (TaskStatus): The status you want to set

    Returns:
        bool: If set successfully
    """
    task = get_task_by_task_title(task_title)
    if task:
        task.status = status
        return True
    return False


def create_queues_from_existing_task_titles(*task_titles: str) -> list[TaskQueue]:
    """Create task queue from titles.

    Args:
        *task_titles (str): The list of task title

    Returns:
        list[TaskQueue]: The queues ordered by requires
    """
    queues_dict: dict[int, TaskQueue] = {}
    for task_title in task_titles:
        task = get_task_by_task_title(task_title)
        if task:
            requires_count = len(task.requires)
            if requires_count in queues_dict:
                queues_dict[requires_count].append(task_title)
            else:
                queues_dict[requires_count] = [task_title]
    keys = list(queues_dict.keys())
    keys.sort()
    return list({key: queues_dict[key] for key in keys}.values())


def clean_string(string: str) -> str:
    """Clean the string.

    Args:
        string (str): The input string

    Returns:
        str The new string which is stripped and replaced newline with space
    """
    return string.strip().replace("\n", "")
