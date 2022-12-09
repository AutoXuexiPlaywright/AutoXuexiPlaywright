from logging import getLogger
from playwright.async_api import Page

from autoxuexiplaywright.defines.core import ProcessType, APPID
from autoxuexiplaywright.defines.selectors import (
    NEWS_TITLE_SPAN, VIDEO_ENTRANCE, VIDEO_LIBRARY, NEWS_LIST, NEWS_TITLE_TEXT, NEXT_PAGE, LOADING,
    VIDEO_TEXT_WRAPPER, TEST_WEEKS, TEST_WEEK_TITLE, TEST_BTN, TEST_WEEK_STAT, TEST_NEXT_PAGE,
    TEST_ITEMS, TEST_SPECIAL_POINTS, TEST_SPECIAL_TITLE, TEST_SPECIAL_TITLE_BEFORE, TEST_SPECIAL_TITLE_AFTER
)
from autoxuexiplaywright.defines.urls import ExamEntranceUrls
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.asyncprocessor.operations import emulate_answer, emulate_read


cache = set[str]()


async def pre_handle(page: Page, close_page: bool, process_type: ProcessType) -> bool:
    skip = True
    match process_type:
        case ProcessType.NEWS:
            async with page.context.expect_page() as page_info:
                await page.locator(NEWS_TITLE_SPAN).click()
            value = await page_info.value
            skip = await handle_news(value)
            await value.close()
        case ProcessType.VIDEO:
            async with page.context.expect_page() as page_info:
                await page.locator(VIDEO_ENTRANCE).first.click()
            value = await page_info.value
            async with value.context.expect_page() as page_info_new:
                await value.locator(VIDEO_LIBRARY).click()
            value_new = await page_info_new.value
            skip = await handle_video(value_new)
            await value_new.close()
            await value.close()
        case ProcessType.TEST:
            skip = await handle_test(page)
        case ProcessType.UNKNOWN:
            getLogger(APPID).error(
                get_lang(Config.get_instance().lang, "core-error-unknown-process-type"))
    if close_page:
        await page.close()
    return skip


async def handle_news(page: Page) -> bool:
    skip = False
    config = Config.get_instance()
    news_list = page.locator(NEWS_LIST)
    await news_list.last.wait_for()
    while True:
        handled_page = False
        for i in range(await news_list.count()):
            title = news_list.nth(i).locator(NEWS_TITLE_TEXT)
            title_text = await title.inner_text()
            if title_text not in cache:
                getLogger(APPID).info(get_lang(
                    config.lang, "core-info-processing-news") % title_text.strip().replace("\n", " "))
                async with page.context.expect_page() as page_info:
                    await title.click()
                value = await page_info.value
                await emulate_read(value)
                cache.add(title_text)
                handled_page = True
                await value.close()
                break
        if not handled_page:
            next_btn = page.locator(NEXT_PAGE)
            getLogger(APPID).warning(get_lang(
                config.lang, "core-warning-no-news-on-current-page"))
            if await next_btn.count() == 0:
                getLogger(APPID).error(get_lang(
                    config.lang, "core-error-no-available-news"))
                skip = True
                break
            else:
                await next_btn.first.click()
                await page.locator(LOADING).wait_for(state="hidden")
        else:
            break
    return skip


async def handle_video(page: Page) -> bool:
    skip = False
    config = Config.get_instance()
    text_wrappers = page.locator(VIDEO_TEXT_WRAPPER)
    while True:
        await text_wrappers.last.wait_for()
        handled_page = False
        for i in range(await text_wrappers.count()):
            text_wrapper = text_wrappers.nth(i)
            text_wrapper_text = await text_wrapper.inner_text()
            if text_wrapper_text not in cache:
                getLogger(APPID).info(
                    get_lang(config.lang, "core-info-processing-video") % text_wrapper_text)
                async with page.context.expect_page() as page_info_video:
                    await text_wrapper.click()
                value = await page_info_video.value
                await emulate_read(value)
                cache.add(text_wrapper_text)
                handled_page = True
                await value.close()
                break
        if not handled_page:
            next_btn = page.locator(NEXT_PAGE)
            getLogger(APPID).warning(get_lang(
                config.lang, "core-warning-no-videos-on-current-page"))
            if await next_btn.count() == 0:
                getLogger(APPID).error(get_lang(
                    config.lang, "core-error-no-available-videos"))
                skip = True
                break
            else:
                await next_btn.first.click()
                await page.locator(LOADING).wait_for(state="hidden")
        else:
            break
    return skip


async def handle_test(page: Page) -> bool:
    skip = False
    config = Config.get_instance()
    match ExamEntranceUrls(page.url):
        case ExamEntranceUrls.DAILY_EXAM_PAGE:
            getLogger(APPID).info(get_lang(
                config.lang, "core-info-processing-daily-test"))
            await emulate_answer(page)
        case ExamEntranceUrls.WEEKLY_EXAM_PAGE:
            while True:
                weeks = page.locator(TEST_WEEKS)
                await weeks.last.wait_for()
                handled_page = False
                for i in range(await weeks.count()):
                    week = weeks.nth(i)
                    title_text = await week.locator(
                        TEST_WEEK_TITLE).inner_text()
                    title = title_text.strip().replace("\n", " ")
                    button = week.locator(TEST_BTN)
                    stat = to_str(await week.locator(
                        TEST_WEEK_STAT).get_attribute("class"))
                    if "done" not in stat:
                        getLogger(APPID).info(
                            get_lang(config.lang, "core-info-processing-weekly-test") % title)
                        await button.click()
                        await emulate_answer(page)
                        handled_page = True
                        break
                if not handled_page:
                    next_btn = page.locator(TEST_NEXT_PAGE)
                    getLogger(APPID).warning(get_lang(
                        config.lang, "core-warning-no-test-on-current-page"))
                    if await next_btn.get_attribute("aria-disabled") == "true":
                        getLogger(APPID).error(get_lang(
                            config.lang, "core-error-no-available-test"))
                        skip = True
                        break
                    elif await next_btn.get_attribute("aria-disabled") == "false":
                        await next_btn.click()
                        await page.locator(LOADING).wait_for(state="hidden")
                    else:
                        break
                else:
                    break
        case ExamEntranceUrls.SPECIAL_EXAM_PAGE:
            while True:
                items = page.locator(TEST_ITEMS)
                await items.last.wait_for()
                handled_page = False
                for i in range(await items.count()):
                    item = items.nth(i)
                    points = item.locator(TEST_SPECIAL_POINTS)
                    button = item.locator(TEST_BTN)
                    title_element = item.locator(
                        TEST_SPECIAL_TITLE)
                    before = await title_element.locator(
                        TEST_SPECIAL_TITLE_BEFORE).inner_text()
                    after = await title_element.locator(
                        TEST_SPECIAL_TITLE_AFTER).inner_text()
                    title_text = await title_element.inner_text()
                    title = title_text.replace(
                        before, "").replace(after, "").strip().replace("\n", " ")
                    if await points.count() == 0:
                        getLogger(APPID).info(
                            get_lang(config.lang, "core-info-processing-special-test") % title)
                        await button.click()
                        await emulate_answer(page)
                        handled_page = True
                        break
                if not handled_page:
                    next_btn = page.locator(TEST_NEXT_PAGE)
                    getLogger(APPID).warning(get_lang(
                        config.lang, "core-warning-no-test-on-current-page"))
                    if await next_btn.get_attribute("aria-disabled") == "true":
                        getLogger(APPID).error(get_lang(
                            config.lang, "core-error-no-available-test"))
                        skip = True
                        break
                    elif await next_btn.get_attribute("aria-disabled") == "false":
                        await next_btn.click()
                        await page.locator(LOADING).wait_for(state="hidden")
                    else:
                        break
                else:
                    break
        case _:
            getLogger(APPID).error(get_lang(
                config.lang, "core-error-unknown-test") % page.url)
            skip = True
    return skip

__all__ = ["pre_handle"]
