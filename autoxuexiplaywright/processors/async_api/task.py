from typing import Literal, Self
from types import TracebackType
from abc import abstractmethod
from playwright.async_api import Locator, Page, TimeoutError
# Relative imports
from ..common import AbstractBaseTask, TaskStatus, get_task_by_task_title
from ...events import EventID, find_event_by_id


class Task(AbstractBaseTask):
    @property
    def last_page(self) -> Page:
        return self.pages[-1]

    def ready(self, page: Page, task_title: str, close: bool = True) -> Self:
        self.pages = [page]
        self.close = close
        self.status = TaskStatus.READY
        find_event_by_id(EventID.STATUS_UPDATED).invoke(task_title)
        return self

    async def _wait_locator(self, locator: Locator, timeout: float | None = None, state: Literal["attached", "detached", "hidden", "visible"] | None = None) -> bool:
        try:
            await locator.wait_for(timeout=timeout, state=state)
        except TimeoutError:
            return False
        return True

    @abstractmethod
    async def finish(self) -> bool: ...

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type: type[Exception] | None, exc_value: Exception | None, trace_back: TracebackType | None) -> bool:
        if self.close and not all([page.is_closed() for page in self.pages]):
            [await page.close() for page in self.pages]
        if self.status == TaskStatus.READY:
            self.status = TaskStatus.SUCCESS
        return all([exc == None for exc in [exc_type, exc_value, trace_back]])


async def do_task(page: Page, task_title: str, close: bool) -> bool:
    """Do the task

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
