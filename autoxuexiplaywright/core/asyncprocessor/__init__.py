from os import remove
from os.path import exists
from time import time
from logging import getLogger
from asyncio import run as asynciorun
from playwright.async_api import Page, TimeoutError, async_playwright

from autoxuexiplaywright.defines.core import (
    ProcessType, WAIT_PAGE_SECS, APPID, WAIT_NEW_PAGE_SECS, NEWS_RANGE, VIDEO_RANGE, TEST_RANGE)
from autoxuexiplaywright.defines.selectors import (
    POINTS_SPAN, POINTS_CARDS, CARD_BUTTON, CARD_TITLE)
from autoxuexiplaywright.defines.urls import POINTS_PAGE
from autoxuexiplaywright.defines.events import EventId
from autoxuexiplaywright.utils.eventmanager import find_event_by_id
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.answerutils import init_sources, close_sources
from autoxuexiplaywright.core.asyncprocessor.handle import cache, pre_handle
from autoxuexiplaywright.core.asyncprocessor.login import login


def start(**kwargs) -> None:
    asynciorun(run(**kwargs))


async def run(**kwargs) -> None:
    cache.clear()
    init_sources(**kwargs)
    start_time = time()
    async with async_playwright() as p:
        browser = await p[kwargs.get("browser", "firefox")].launch(
            headless=not kwargs.get("debug", False), proxy=kwargs.get("proxy"),
            channel=kwargs.get("channel"), args=["--mute-audio"], devtools=not kwargs.get("debug", False),
            firefox_user_prefs={"media.volume_scale": "0.0"}, executable_path=kwargs.get("executable_path", None))
        if exists(get_cache_path("cookies.json")):
            context = await browser.new_context(
                storage_state=get_cache_path("cookies.json"))
        else:
            context = await browser.new_context()
        context.set_default_timeout(WAIT_PAGE_SECS*1000)
        try:
            await login(await context.new_page(), **kwargs)
            await check_status_and_finish(
                await context.new_page(),  **kwargs)
        except Exception as e:
            getLogger(APPID).error(get_lang(
                kwargs.get("lang", "zh-cn"), "core-err-process-exception") % e)
        await context.close()
        await browser.close()
    close_sources()
    if not kwargs.get("debug", False):
        if exists(get_cache_path("video.mp4")):
            remove(get_cache_path("video.mp4"))
        if exists(get_cache_path("qr.png")):
            remove(get_cache_path("qr.png"))
    delta_mins, delta_secs = divmod(time.time()-start_time, 60)
    delta_hrs, delta_mins = divmod(delta_mins, 60)
    finish_str = get_lang(kwargs.get(
        "lang", "zh-cn"), "core-info-all-finished").format(int(delta_hrs), int(delta_mins), int(delta_secs))
    getLogger(APPID).info(finish_str)
    find_event_by_id(EventId.FINISHED).invoke(finish_str)


async def check_status_and_finish(page: Page, **kwargs):
    process_position = 1  # login must be finished on app
    while True:
        await page.goto(POINTS_PAGE)
        try:
            points = page.locator(POINTS_SPAN)
            for i in range(2):
                await points.nth(i).wait_for()
            points_ints = tuple([int(point.strip())
                                for point in await points.all_inner_texts()])
        except:
            getLogger(APPID).error(get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-update-score-failed"))
        else:
            getLogger(APPID).info(get_lang(kwargs.get(
                "lang", "zh-cn"), "core-info-update-score-success") % points_ints)
            find_event_by_id(
                EventId.SCORE_UPDATED).invoke(points_ints)
        cards = page.locator(POINTS_CARDS)
        await cards.last.wait_for()
        login_task_style = to_str(await cards.nth(0).locator(
            CARD_BUTTON).first.get_attribute("style"))
        if "not-allowed" not in login_task_style:
            getLogger(APPID).warning(get_lang(kwargs.get(
                "lang", "zh-cn"), "core-warning-login-task-not-completed"))
        if process_position < await cards.count():
            card = cards.nth(process_position)
            title = await card.locator(CARD_TITLE).first.inner_text()
            button = card.locator(CARD_BUTTON).first
            style = to_str(await button.get_attribute("style"))
            if "not-allowed" in style:
                getLogger(APPID).info(get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-finished") % title)
                process_position += 1
            elif title.strip() in kwargs.get("skipped_items", []):
                getLogger(APPID).info(get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-skipped") % title)
                process_position += 1
            else:
                getLogger(APPID).info(get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-processing") % title)
                find_event_by_id(EventId.STATUS_UPDATED).invoke(
                    get_lang(kwargs.get(
                        "lang", "zh-cn"), "ui-status-tooltip") % title)
                try:
                    async with page.context.expect_page(timeout=WAIT_NEW_PAGE_SECS*1000) as page_event:
                        await button.click()
                except TimeoutError:
                    target_page = page
                    close_page = False
                else:
                    target_page = page_event.value
                    close_page = True
                if process_position in NEWS_RANGE:
                    process_type = ProcessType.NEWS
                elif process_position in VIDEO_RANGE:
                    process_type = ProcessType.VIDEO
                elif process_position in TEST_RANGE:
                    process_type = ProcessType.TEST
                else:
                    process_type = ProcessType.UNKNOWN
                if await pre_handle(target_page, close_page, process_type,  **kwargs):
                    process_position += 1
                await page.context.storage_state(
                    path=get_cache_path("cookies.json"))
        else:
            break
    await page.close()

__all__ = ["start"]
