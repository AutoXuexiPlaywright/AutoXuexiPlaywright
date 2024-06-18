"""classes and functions for async mode."""

from time import time

# Relative imports
from .task import do_task
from asyncio import Task
from asyncio import TaskGroup
from asyncio import run
from ..common import WAIT_PAGE_SECS
from ..common import TaskQueue
from ..common import TaskStatus
from ..common import scores
from ..common import tasks_to_be_done
from ..common import set_task_status_by_task_title
from ..common import create_queues_from_existing_task_titles
from ...config import get_runtime_config
from ...events import EventID
from ...events import find_event_by_id
from ...logger import info
from ...logger import debug
from ...logger import error
from ...logger import warning
from ...storage import get_cache_path
from ...languages import get_language_string
from ..common.urls import POINTS_PAGE
from ..common.selectors import PointsSelectors
from playwright.async_api import Page
from playwright.async_api import Locator
from playwright.async_api import BrowserContext
from playwright.async_api import async_playwright


_config = get_runtime_config()


async def _is_card_finished(card: Locator) -> bool:
    progress_value = 0.0
    progress = card.locator(PointsSelectors.CARD_PROGRESS).first
    style = await progress.get_attribute("style") or ""
    if style.startswith("width"):
        progress_percent = (
            style.removeprefix("width").replace(":", "").removesuffix(";").strip().removesuffix("%")
        )
        try:
            progress_value = float(progress_percent) / 100
        except ValueError:
            warning(get_language_string("core-warning-failed-to-parse-progress"))
    return progress_value == 1.0


async def _get_status_from_page(page: Page, close: bool) -> bool:
    await page.goto(POINTS_PAGE)
    tasks_to_be_done.clear()

    points = page.locator(PointsSelectors.POINTS_SPAN)
    try:
        await points.nth(0).wait_for()
        await points.nth(1).wait_for()
        scores[0] = int(await points.nth(0).inner_text())
        scores[1] = int(await points.nth(1).inner_text())
    except ValueError:
        error(get_language_string("core-error-update-score-failed"))
    else:
        info(get_language_string("core-info-update-score-success") % tuple(scores))

    cards = page.locator(PointsSelectors.POINTS_CARDS)
    await cards.last.wait_for()
    for i in range(await cards.count()):
        card = cards.nth(i)
        title = (await card.locator(PointsSelectors.CARD_TITLE).first.inner_text()).strip()
        if (title in _config.skipped) and not set_task_status_by_task_title(
            title,
            TaskStatus.SKIPPED,
        ):
            warning(get_language_string("core-warning-failed-to-skip-task") % title)
        elif (not await _is_card_finished(card)) and (title not in tasks_to_be_done):
            tasks_to_be_done.append(title)
    find_event_by_id(EventID.SCORE_UPDATED).invoke(tuple(scores))

    if close and not page.is_closed():
        await page.close()
    return len(tasks_to_be_done) == 0


async def _finish_queue(queue: TaskQueue, context: BrowserContext, close: bool):
    debug(
        get_language_string("core-debug-current-queue") % ", ".join([str(task) for task in queue]),
    )
    results: list[bool] = []
    for task in queue:
        task_result = await do_task(await context.new_page(), task, close)
        debug(get_language_string("core-debug-task-result") % (str(task), str(task_result)))
        results.append(task_result)
    if not all(results):
        warning(get_language_string("core-warning-some-tasks-failed"))


async def _finish_all(context: BrowserContext, close: bool = True):
    await do_task(await context.new_page(), "登录", close)
    while not await _get_status_from_page(await context.new_page(), close):
        debug(get_language_string("core-debug-task-to-be-done-is") % str(tasks_to_be_done))
        queues = create_queues_from_existing_task_titles(*tasks_to_be_done)
        tasks: list[Task[None]] = []
        async with TaskGroup() as tg:
            for queue in queues:
                tasks.append(tg.create_task(_finish_queue(queue, context, close)))

    if close:
        for page in context.pages:
            if not page.is_closed():
                await page.close()


async def _start():
    start_time = time()
    async with async_playwright() as p:
        context = await p[_config.browser_id].launch_persistent_context(
            user_data_dir=get_cache_path("browser-data") / _config.browser_id,
            headless=not _config.debug,
            proxy=_config.proxy,
            channel=_config.browser_channel,
            args=["--mute-audio"],
            devtools=not _config.debug,
            executable_path=_config.executable_path,
            firefox_user_prefs={"media.volume_scale": "0.0"},
        )

        context.set_default_timeout(WAIT_PAGE_SECS * 1000)
        try:
            await _finish_all(context)
        except Exception as e:
            error(get_language_string("core-err-process-exception") % e)
        finally:
            await context.close()
    delta_mins, delta_secs = divmod(time() - start_time, 60)
    delta_hrs, delta_mins = divmod(delta_mins, 60)
    finish_str = get_language_string("core-info-all-finished").format(
        int(delta_hrs),
        int(delta_mins),
        int(delta_secs),
    )
    info(finish_str)
    find_event_by_id(EventID.FINISHED).invoke(finish_str)


def start():
    """Main entrance to wrapper asyncio."""
    run(_start())
