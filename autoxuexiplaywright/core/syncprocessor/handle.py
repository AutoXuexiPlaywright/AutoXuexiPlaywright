import logging
from playwright.sync_api import Page
from autoxuexiplaywright.defines import core, selectors, urls
from autoxuexiplaywright.utils import lang, misc
from autoxuexiplaywright.core.syncprocessor.operations import emulate_answer, emulate_read


cache = set[str]()


def pre_handle(page: Page, close_page: bool, process_type: core.ProcessType,  **kwargs) -> bool:
    skip = True
    match process_type:
        case core.ProcessType.NEWS:
            with page.context.expect_page() as page_info:
                page.locator(selectors.NEWS_TITLE_SPAN).click()
            skip = handle_news(page_info.value, **kwargs)
            page_info.value.close()
        case core.ProcessType.VIDEO:
            page.locator(selectors.VIDEO_ENTRANCE).hover()
            with page.context.expect_page() as page_info:
                page.locator(selectors.VIDEO_ENTRANCE).click()
            with page_info.value.context.expect_page() as page_info_new:
                page_info.value.locator(selectors.VIDEO_LIBRARY).click()
            skip = handle_video(page_info_new.value, **kwargs)
            page_info_new.value.close()
            page_info.value.close()
        case core.ProcessType.TEST:
            skip = handle_test(page,  **kwargs)
    if close_page:
        page.close()
    return skip


def handle_news(page: Page, **kwargs) -> bool:
    skip = False
    news_list = page.locator(selectors.NEWS_LIST)
    news_list.last.wait_for()
    while True:
        handled_page = False
        for i in range(news_list.count()):
            title = news_list.nth(i).locator(selectors.NEWS_TITLE_TEXT)
            if title.inner_text() not in cache:
                logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-info-processing-news") % title.inner_text().strip().replace("\n", " "))
                with page.context.expect_page() as page_info:
                    title.click()
                emulate_read(page_info.value)
                cache.add(title.inner_text())
                handled_page = True
                page_info.value.close()
                break
        if not handled_page:
            next_btn = page.locator(selectors.NEXT_PAGE)
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-no-news-on-current-page"))
            if next_btn.count() == 0:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-error-no-available-news"))
                skip = True
                break
            else:
                next_btn.first.click()
                page.locator(selectors.LOADING).wait_for(state="hidden")
        else:
            break
    return skip


def handle_video(page: Page, **kwargs) -> bool:
    skip = False
    text_wrappers = page.locator(selectors.VIDEO_TEXT_WRAPPER)
    while True:
        text_wrappers.last.wait_for()
        handled_page = False
        for i in range(text_wrappers.count()):
            text_wrapper = text_wrappers.nth(i)
            if text_wrapper.inner_text() not in cache:
                logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-info-processing-video") % text_wrapper.inner_text())
                with page.context.expect_page() as page_info_video:
                    text_wrapper.click()
                emulate_read(page_info_video.value, **kwargs)
                cache.add(text_wrapper.inner_text())
                handled_page = True
                page_info_video.value.close()
                break
        if not handled_page:
            next_btn = page.locator(selectors.NEXT_PAGE)
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-no-videos-on-current-page"))
            if next_btn.count() == 0:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-error-no-available-videos"))
                skip = True
                break
            else:
                next_btn.first.click()
                page.locator(selectors.LOADING).wait_for(state="hidden")
        else:
            break
    return skip


def handle_test(page: Page,  **kwargs) -> bool:
    skip = False
    if page.url == urls.DAILY_EXAM_PAGE:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-processing-daily-test"))
        emulate_answer(page, **kwargs)
    elif page.url == urls.WEEKLY_EXAM_PAGE:
        while True:
            weeks = page.locator(selectors.TEST_WEEKS)
            weeks.last.wait_for()
            handled_page = False
            for i in range(weeks.count()):
                week = weeks.nth(i)
                title = week.locator(
                    selectors.TEST_WEEK_TITLE).inner_text().strip().replace("\n", " ")
                button = week.locator(selectors.TEST_BTN)
                stat = misc.to_str(week.locator(
                    selectors.TEST_WEEK_STAT).get_attribute("class"))
                if "done" not in stat:
                    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-info-processing-weekly-test") % title)
                    button.click()
                    emulate_answer(page, **kwargs)
                    handled_page = True
                    break
            if not handled_page:
                next_btn = page.locator(selectors.TEST_NEXT_PAGE)
                logging.getLogger(core.APPID).warning(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-warning-no-test-on-current-page"))
                if next_btn.get_attribute("aria-disabled") == "true":
                    logging.getLogger(core.APPID).error(lang.get_lang(
                        kwargs.get("lang", "zh-cn"), "core-error-no-available-test"))
                    skip = True
                    break
                elif next_btn.get_attribute("aria-disabled") == "false":
                    next_btn.click()
                    page.locator(selectors.LOADING).wait_for(state="hidden")
                else:
                    break
            else:
                break
    elif page.url == urls.SPECIAL_EXAM_PAGE:
        while True:
            items = page.locator(selectors.TEST_ITEMS)
            items.last.wait_for()
            handled_page = False
            for i in range(items.count()):
                item = items.nth(i)
                points = item.locator(selectors.TEST_SPECIAL_POINTS)
                button = item.locator(selectors.TEST_BTN)
                title_element = item.locator(
                    selectors.TEST_SPECIAL_TITLE)
                before = title_element.locator(
                    selectors.TEST_SPECIAL_TITLE_BEFORE).inner_text()
                after = title_element.locator(
                    selectors.TEST_SPECIAL_TITLE_AFTER).inner_text()
                title = title_element.inner_text().replace(
                    before, "").replace(after, "").strip().replace("\n", " ")
                if points.count() == 0:
                    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-info-processing-special-test") % title)
                    button.click()
                    emulate_answer(page,  **kwargs)
                    handled_page = True
                    break
            if not handled_page:
                next_btn = page.locator(selectors.TEST_NEXT_PAGE)
                logging.getLogger(core.APPID).warning(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-warning-no-test-on-current-page"))
                if next_btn.get_attribute("aria-disabled") == "true":
                    logging.getLogger(core.APPID).error(lang.get_lang(
                        kwargs.get("lang", "zh-cn"), "core-error-no-available-test"))
                    skip = True
                    break
                elif next_btn.get_attribute("aria-disabled") == "false":
                    next_btn.click()
                    page.locator(selectors.LOADING).wait_for(state="hidden")
                else:
                    break
            else:
                break
    else:
        logging.getLogger(core.APPID).error(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-error-unknown-test"))
        skip = True
    return skip


__all__ = ["pre_handle"]
