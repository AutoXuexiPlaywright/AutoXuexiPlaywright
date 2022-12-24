from logging import getLogger
from playwright.sync_api import Page

from autoxuexiplaywright.defines.core import ProcessType
from autoxuexiplaywright.defines.selectors import ReadSelectors, AnswerSelectors, LOADING
from autoxuexiplaywright.defines.urls import ExamEntranceUrls
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils .misc import to_str
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.syncprocessor.operations import emulate_answer, emulate_read

from autoxuexiplaywright import appid


cache = set[str]()


def pre_handle(page: Page, close_page: bool, process_type: ProcessType) -> bool:
    skip = True
    match process_type:
        case ProcessType.NEWS:
            with page.context.expect_page() as page_info:
                page.locator(ReadSelectors.NEWS_TITLE_SPAN).click()
            skip = handle_news(page_info.value)
            page_info.value.close()
        case ProcessType.VIDEO:
            with page.context.expect_page() as page_info:
                page.locator(ReadSelectors.VIDEO_ENTRANCE).first.click()
            with page_info.value.context.expect_page() as page_info_new:
                page_info.value.locator(ReadSelectors.VIDEO_LIBRARY).click()
            skip = handle_video(page_info_new.value)
            page_info_new.value.close()
            page_info.value.close()
        case ProcessType.TEST:
            skip = handle_test(page)
        case ProcessType.UNKNOWN:
            getLogger(appid).error(
                get_lang(Config.get_instance().lang, "core-error-unknown-process-type"))
    if close_page:
        page.close()
    return skip


def handle_news(page: Page) -> bool:
    skip = False
    config = Config.get_instance()
    news_list = page.locator(ReadSelectors.NEWS_LIST)
    news_list.last.wait_for()
    while True:
        handled_page = False
        for i in range(news_list.count()):
            title = news_list.nth(i).locator(ReadSelectors.NEWS_TITLE_TEXT)
            if title.inner_text() not in cache:
                getLogger(appid).info(get_lang(config.lang, "core-info-processing-news") %
                                      title.inner_text().strip().replace("\n", " "))
                with page.context.expect_page() as page_info:
                    title.click()
                emulate_read(page_info.value)
                cache.add(title.inner_text())
                handled_page = True
                page_info.value.close()
                break
        if not handled_page:
            next_btn = page.locator(ReadSelectors.NEXT_PAGE)
            getLogger(appid).warning(get_lang(
                config.lang, "core-warning-no-news-on-current-page"))
            if next_btn.count() == 0:
                getLogger(appid).error(get_lang(
                    config.lang, "core-error-no-available-news"))
                skip = True
                break
            else:
                next_btn.first.click()
                page.locator(LOADING).wait_for(state="hidden")
        else:
            break
    return skip


def handle_video(page: Page) -> bool:
    skip = False
    config = Config.get_instance()
    text_wrappers = page.locator(ReadSelectors.VIDEO_TEXT_WRAPPER)
    while True:
        text_wrappers.last.wait_for()
        handled_page = False
        for i in range(text_wrappers.count()):
            text_wrapper = text_wrappers.nth(i)
            if text_wrapper.inner_text() not in cache:
                getLogger(appid).info(get_lang(
                    config.lang, "core-info-processing-video") % text_wrapper.inner_text())
                with page.context.expect_page() as page_info_video:
                    text_wrapper.click()
                emulate_read(page_info_video.value)
                cache.add(text_wrapper.inner_text())
                handled_page = True
                page_info_video.value.close()
                break
        if not handled_page:
            next_btn = page.locator(ReadSelectors.NEXT_PAGE)
            getLogger(appid).warning(get_lang(
                config.lang, "core-warning-no-videos-on-current-page"))
            if next_btn.count() == 0:
                getLogger(appid).error(get_lang(
                    config.lang, "core-error-no-available-videos"))
                skip = True
                break
            else:
                next_btn.first.click()
                page.locator(LOADING).wait_for(state="hidden")
        else:
            break
    return skip


def handle_test(page: Page) -> bool:
    skip = False
    config = Config.get_instance()
    match page.url:
        case ExamEntranceUrls.DAILY_EXAM_PAGE:
            getLogger(appid).info(get_lang(
                config.lang, "core-info-processing-daily-test"))
            emulate_answer(page)
        case ExamEntranceUrls.WEEKLY_EXAM_PAGE:
            while True:
                weeks = page.locator(AnswerSelectors.TEST_WEEKS)
                weeks.last.wait_for()
                handled_page = False
                for i in range(weeks.count()):
                    week = weeks.nth(i)
                    title = week.locator(
                        AnswerSelectors.TEST_WEEK_TITLE).inner_text().strip().replace("\n", " ")
                    button = week.locator(AnswerSelectors.TEST_BTN)
                    stat = to_str(week.locator(
                        AnswerSelectors.TEST_WEEK_STAT).get_attribute("class"))
                    if "done" not in stat:
                        getLogger(appid).info(
                            get_lang(config.lang, "core-info-processing-weekly-test") % title)
                        button.click()
                        emulate_answer(page)
                        handled_page = True
                        break
                if not handled_page:
                    next_btn = page.locator(AnswerSelectors.TEST_NEXT_PAGE)
                    getLogger(appid).warning(get_lang(
                        config.lang, "core-warning-no-test-on-current-page"))
                    if next_btn.get_attribute("aria-disabled") == "true":
                        getLogger(appid).error(get_lang(
                            config.lang, "core-error-no-available-test"))
                        skip = True
                        break
                    elif next_btn.get_attribute("aria-disabled") == "false":
                        next_btn.click()
                        page.locator(LOADING).wait_for(state="hidden")
                    else:
                        break
                else:
                    break
        case ExamEntranceUrls.SPECIAL_EXAM_PAGE:
            while True:
                items = page.locator(AnswerSelectors.TEST_ITEMS)
                items.last.wait_for()
                handled_page = False
                for i in range(items.count()):
                    item = items.nth(i)
                    points = item.locator(AnswerSelectors.TEST_SPECIAL_POINTS)
                    button = item.locator(AnswerSelectors.TEST_BTN)
                    title_element = item.locator(
                        AnswerSelectors.TEST_SPECIAL_TITLE)
                    before = title_element.locator(
                        AnswerSelectors.TEST_SPECIAL_TITLE_BEFORE).inner_text()
                    after = title_element.locator(
                        AnswerSelectors.TEST_SPECIAL_TITLE_AFTER).inner_text()
                    title = title_element.inner_text().replace(
                        before, "").replace(after, "").strip().replace("\n", " ")
                    if points.count() == 0:
                        getLogger(appid).info(
                            get_lang(config.lang, "core-info-processing-special-test") % title)
                        button.click()
                        emulate_answer(page)
                        handled_page = True
                        break
                if not handled_page:
                    next_btn = page.locator(AnswerSelectors.TEST_NEXT_PAGE)
                    getLogger(appid).warning(get_lang(
                        config.lang, "core-warning-no-test-on-current-page"))
                    if next_btn.get_attribute("aria-disabled") == "true":
                        getLogger(appid).error(get_lang(
                            config.lang, "core-error-no-available-test"))
                        skip = True
                        break
                    elif next_btn.get_attribute("aria-disabled") == "false":
                        next_btn.click()
                        page.locator(LOADING).wait_for(state="hidden")
                    else:
                        break
                else:
                    break
        case url:
            getLogger(appid).error(get_lang(
                config.lang, "core-error-unknown-test") % url)
            skip = True
    return skip


__all__ = ["pre_handle"]
