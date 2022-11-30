import os
import time
import logging
from autoxuexiplaywright.defines import urls, core, selectors, events
from autoxuexiplaywright.utils import misc, lang, answerutils, storage, eventmanager
from playwright.sync_api import Page, TimeoutError, sync_playwright
from autoxuexiplaywright.core.syncprocessor.login import login
from autoxuexiplaywright.core.syncprocessor.handle import cache, pre_handle


def run(**kwargs) -> None:
    cache.clear()
    answerutils.init_sources(**kwargs)
    start_time = time.time()
    with sync_playwright() as p:
        browser = p[kwargs.get("browser", "firefox")].launch(
            headless=not kwargs.get("debug", False), proxy=kwargs.get("proxy"),
            channel=kwargs.get("channel"), args=["--mute-audio"], devtools=not kwargs.get("debug", False),
            firefox_user_prefs={"media.volume_scale": "0.0"}, executable_path=kwargs.get("executable_path", None))
        if os.path.exists(storage.get_cache_path("cookies.json")):
            context = browser.new_context(
                storage_state=storage.get_cache_path("cookies.json"))
        else:
            context = browser.new_context()
        context.set_default_timeout(core.WAIT_PAGE_SECS*1000)
        try:
            login(context.new_page(), **kwargs)
            check_status_and_finish(
                context.new_page(),  **kwargs)
        except Exception as e:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-err-process-exception") % e)
        context.close()
        browser.close()
    answerutils.close_sources()
    if not kwargs.get("debug", False):
        if os.path.exists(storage.get_cache_path("video.mp4")):
            os.remove(storage.get_cache_path("video.mp4"))
        if os.path.exists(storage.get_cache_path("qr.png")):
            os.remove(storage.get_cache_path("qr.png"))
    delta_mins, delta_secs = divmod(time.time()-start_time, 60)
    delta_hrs, delta_mins = divmod(delta_mins, 60)
    finish_str = lang.get_lang(kwargs.get(
        "lang", "zh-cn"), "core-info-all-finished").format(int(delta_hrs), int(delta_mins), int(delta_secs))
    logging.getLogger(core.APPID).info(finish_str)
    eventmanager.find_event_by_id(events.EventId.FINISHED).invoke(finish_str)


def check_status_and_finish(page: Page,  **kwargs) -> None:
    process_position = 1  # login must be finished on app
    while True:
        page.goto(urls.POINTS_PAGE)
        try:
            points = page.locator(selectors.POINTS_SPAN)
            for i in range(2):
                points.nth(i).wait_for()
            points_ints = tuple([int(point.strip())
                                for point in points.all_inner_texts()])
        except:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-update-score-failed"))
        else:
            logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-info-update-score-success") % points_ints)
            eventmanager.find_event_by_id(
                events.EventId.SCORE_UPDATED).invoke(points_ints)
        cards = page.locator(selectors.POINTS_CARDS)
        cards.last.wait_for()
        login_task_style = misc.to_str(cards.nth(0).locator(
            selectors.CARD_BUTTON).first.get_attribute("style"))
        if "not-allowed" not in login_task_style:
            logging.getLogger(core.APPID).warning(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-warning-login-task-not-completed"))
        if process_position < cards.count():
            card = cards.nth(process_position)
            title = card.locator(selectors.CARD_TITLE).first.inner_text()
            button = card.locator(selectors.CARD_BUTTON).first
            style = misc.to_str(button.get_attribute("style"))
            if "not-allowed" in style:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-finished") % title)
                process_position += 1
            elif title.strip() in kwargs.get("skipped_items", []):
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-skipped") % title)
                process_position += 1
            else:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-processing") % title)
                eventmanager.find_event_by_id(events.EventId.STATUS_UPDATED).invoke(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "ui-status-tooltip") % title)
                try:
                    with page.context.expect_page(timeout=core.WAIT_NEW_PAGE_SECS*1000) as page_event:
                        button.click()
                except TimeoutError:
                    target_page = page
                    close_page = False
                else:
                    target_page = page_event.value
                    close_page = True
                if process_position in core.NEWS_RANGE:
                    process_type = core.ProcessType.NEWS
                elif process_position in core.VIDEO_RANGE:
                    process_type = core.ProcessType.VIDEO
                elif process_position in core.TEST_RANGE:
                    process_type = core.ProcessType.TEST
                else:
                    process_type = core.ProcessType.UNKNOWN
                if pre_handle(target_page, close_page, process_type,  **kwargs):
                    process_position += 1
                page.context.storage_state(
                    path=storage.get_cache_path("cookies.json"))
        else:
            break
    page.close()


start = run

__all__ = ["start"]
