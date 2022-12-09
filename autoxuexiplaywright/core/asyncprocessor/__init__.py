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
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.core.asyncprocessor.handle import cache, pre_handle
from autoxuexiplaywright.core.asyncprocessor.login import login


def start(conf_path: str | None = None) -> None:
    asynciorun(run(conf_path))


async def run(conf_path: str | None) -> None:
    config = Config.get_instance(conf_path)
    cache.clear()
    init_sources()
    start_time = time()
    async with async_playwright() as p:
        browser = await p[config.browser_id].launch(
            headless=not config.debug, proxy=config.proxy,
            channel=config.channel, args=["--mute-audio"], devtools=not config.debug,
            firefox_user_prefs={"media.volume_scale": "0.0"}, executable_path=config.executable_path)
        if exists(get_cache_path("cookies.json")):
            context = await browser.new_context(
                storage_state=get_cache_path("cookies.json"))
        else:
            context = await browser.new_context()
        context.set_default_timeout(WAIT_PAGE_SECS*1000)
        try:
            await login(await context.new_page())
            await check_status_and_finish(
                await context.new_page())
        except Exception as e:
            getLogger(APPID).error(get_lang(
                config.lang, "core-err-process-exception") % e)
        await context.close()
        await browser.close()
    close_sources()
    if not config.debug:
        if exists(get_cache_path("video.mp4")):
            remove(get_cache_path("video.mp4"))
        if exists(get_cache_path("qr.png")):
            remove(get_cache_path("qr.png"))
    delta_mins, delta_secs = divmod(time()-start_time, 60)
    delta_hrs, delta_mins = divmod(delta_mins, 60)
    finish_str = get_lang(config.lang, "core-info-all-finished").format(int(delta_hrs), int(delta_mins), int(delta_secs))
    getLogger(APPID).info(finish_str)
    find_event_by_id(EventId.FINISHED).invoke(finish_str)


async def check_status_and_finish(page: Page):
    process_position = 1  # login must be finished on app
    config = Config.get_instance()
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
                config.lang, "core-error-update-score-failed"))
        else:
            getLogger(APPID).info(get_lang(config.lang, "core-info-update-score-success") % points_ints)
            find_event_by_id(
                EventId.SCORE_UPDATED).invoke(points_ints)
        cards = page.locator(POINTS_CARDS)
        await cards.last.wait_for()
        login_task_style = to_str(await cards.nth(0).locator(
            CARD_BUTTON).first.get_attribute("style"))
        if "not-allowed" not in login_task_style:
            getLogger(APPID).warning(get_lang(config.lang, "core-warning-login-task-not-completed"))
        if process_position < await cards.count():
            card = cards.nth(process_position)
            title = await card.locator(CARD_TITLE).first.inner_text()
            button = card.locator(CARD_BUTTON).first
            style = to_str(await button.get_attribute("style"))
            if "not-allowed" in style:
                getLogger(APPID).info(get_lang(
                    config.lang, "core-info-card-finished") % title)
                process_position += 1
            elif title.strip() in config.skipped:
                getLogger(APPID).info(get_lang(
                    config.lang, "core-info-card-skipped") % title)
                process_position += 1
            else:
                getLogger(APPID).info(get_lang(
                    config.lang, "core-info-card-processing") % title)
                find_event_by_id(EventId.STATUS_UPDATED).invoke(
                    get_lang(config.lang, "ui-status-tooltip") % title)
                try:
                    async with page.context.expect_page(timeout=WAIT_NEW_PAGE_SECS*1000) as page_event:
                        await button.click()
                except TimeoutError:
                    target_page = page
                    close_page = False
                else:
                    target_page = await page_event.value
                    close_page = True
                if process_position in NEWS_RANGE:
                    process_type = ProcessType.NEWS
                elif process_position in VIDEO_RANGE:
                    process_type = ProcessType.VIDEO
                elif process_position in TEST_RANGE:
                    process_type = ProcessType.TEST
                else:
                    process_type = ProcessType.UNKNOWN
                if await pre_handle(target_page, close_page, process_type):
                    process_position += 1
                await page.context.storage_state(
                    path=get_cache_path("cookies.json"))
        else:
            break
    await page.close()

__all__ = ["start"]
