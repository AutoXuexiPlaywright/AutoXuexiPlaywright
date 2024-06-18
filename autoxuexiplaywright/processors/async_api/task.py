"""Task abstract class and functions."""

from abc import abstractmethod
from types import TracebackType
from typing import Self
from typing import Literal
from ..common import TaskStatus

# Relative imports
from ..common import AbstractBaseTask
from ..common import get_task_by_task_title
from ...events import EventID
from ...events import find_event_by_id
from playwright.async_api import Page
from playwright.async_api import Locator
from playwright.async_api import TimeoutError


class Task(AbstractBaseTask):
    """Base Task class."""

    @property
    def last_page(self) -> Page:
        """The latest page."""
        return self.pages[-1]

    def ready(self, page: Page, task_title: str, close: bool = True) -> Self:
        """Make task handler ready.

        Args:
            page(Page): The page to work on
            task_title(str): The task's name
            close(bool): Close the page after finished, defaults to True
        """
        self.pages = [page]
        self.close = close
        self.status = TaskStatus.READY
        find_event_by_id(EventID.STATUS_UPDATED).invoke(task_title)
        return self

    async def _wait_locator(
        self,
        locator: Locator,
        timeout: float | None = None,
        state: Literal["attached", "detached", "hidden", "visible"] | None = None,
    ) -> bool:
        try:
            await locator.wait_for(timeout=timeout, state=state)
        except TimeoutError:
            return False
        return True

    @abstractmethod
    async def finish(self) -> bool:
        """Finish the task."""

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Implements context manager."""

    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc_value: Exception | None,
        trace_back: TracebackType | None,
    ) -> bool:
        """Implements context manager."""
        if self.close and not all(page.is_closed() for page in self.pages):
            [await page.close() for page in self.pages]
        if self.status == TaskStatus.READY:
            self.status = TaskStatus.SUCCESS
        return all(not exc for exc in [exc_type, exc_value, trace_back])


async def do_task(page: Page, task_title: str, close: bool) -> bool:
    """Do the task.

    Args:
        page (Page): The page assaigned to the task
        task_title (str): The title of task on status page
        close (bool): If close the `page` after finished task

    Returns:
        bool: If found task and finished it successfully
    """
    task = get_task_by_task_title(task_title)
    if isinstance(task, Task):
        if task.status == TaskStatus.SKIPPED:
            if close and not page.is_closed():
                await page.close()
            return True
        async with task.ready(page, task_title, close) as t:
            result = await t.finish()
            if close and not page.is_closed():
                await page.close()
            return result
    if close and not page.is_closed():
        await page.close()
    return False
