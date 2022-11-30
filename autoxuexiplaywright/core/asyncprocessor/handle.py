import logging
from playwright.async_api import Page
from autoxuexiplaywright.defines import core, selectors, urls
from autoxuexiplaywright.utils import misc, lang
from autoxuexiplaywright.core.asyncprocessor.operations import emulate_answer, emulate_read


cache = set[str]()


async def pre_handle(page: Page, close_page: bool, process_type: core.ProcessType,  **kwargs) -> bool:
    skip = True
    match process_type:
        case core.ProcessType.NEWS:
            async with page.context.expect_page() as page_info:
                await page.locator(selectors.NEWS_TITLE_SPAN).click()
            value = await page_info.value
            skip = await handle_news(value, **kwargs)
            await value.close()
        case core.ProcessType.VIDEO:
            await page.locator(selectors.VIDEO_ENTRANCE).hover()
            async with page.context.expect_page() as page_info:
                await page.locator(selectors.VIDEO_ENTRANCE).click()
            value = await page_info.value
            async with value.context.expect_page() as page_info_new:
                await value.locator(selectors.VIDEO_LIBRARY).click()
            value_new = await page_info_new.value
            skip = await handle_video(value_new, **kwargs)
            await value_new.close()
            await value.close()
        case core.ProcessType.TEST:
            skip = await handle_test(page,  **kwargs)
    if close_page:
        await page.close()
    return skip


async def handle_news(page: Page, **kwargs) -> bool:
    skip = False
    news_list = page.locator(selectors.NEWS_LIST)
    await news_list.last.wait_for()
    while True:
        handled_page = False
        for i in range(await news_list.count()):
            title = news_list.nth(i).locator(selectors.NEWS_TITLE_TEXT)
            title_text = await title.inner_text()
            if title_text not in cache:
                logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-info-processing-news") % title_text.strip().replace("\n", " "))
                async with page.context.expect_page() as page_info:
                    await title.click()
                value = await page_info.value
                await emulate_read(value)
                cache.add(title_text)
                handled_page = True
                await value.close()
                break
        if not handled_page:
            next_btn = page.locator(selectors.NEXT_PAGE)
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-no-news-on-current-page"))
            if await next_btn.count() == 0:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-error-no-available-news"))
                skip = True
                break
            else:
                await next_btn.first.click()
                await page.locator(selectors.LOADING).wait_for(state="hidden")
        else:
            break
    return skip


async def handle_video(page: Page, **kwargs) -> bool:
    skip = False
    text_wrappers = page.locator(selectors.VIDEO_TEXT_WRAPPER)
    while True:
        await text_wrappers.last.wait_for()
        handled_page = False
        for i in range(await text_wrappers.count()):
            text_wrapper = text_wrappers.nth(i)
            text_wrapper_text = await text_wrapper.inner_text()
            if text_wrapper_text not in cache:
                logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-info-processing-video") % text_wrapper_text)
                async with page.context.expect_page() as page_info_video:
                    await text_wrapper.click()
                value = await page_info_video.value
                await emulate_read(value, **kwargs)
                cache.add(text_wrapper_text)
                handled_page = True
                await value.close()
                break
        if not handled_page:
            next_btn = page.locator(selectors.NEXT_PAGE)
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-no-videos-on-current-page"))
            if await next_btn.count() == 0:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-error-no-available-videos"))
                skip = True
                break
            else:
                await next_btn.first.click()
                await page.locator(selectors.LOADING).wait_for(state="hidden")
        else:
            break
    return skip


async def handle_test(page: Page,  **kwargs) -> bool:
    skip = False
    if page.url == urls.DAILY_EXAM_PAGE:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-processing-daily-test"))
        await emulate_answer(page, **kwargs)
    elif page.url == urls.WEEKLY_EXAM_PAGE:
        while True:
            weeks = page.locator(selectors.TEST_WEEKS)
            await weeks.last.wait_for()
            handled_page = False
            for i in range(await weeks.count()):
                week = weeks.nth(i)
                title_text = await week.locator(
                    selectors.TEST_WEEK_TITLE).inner_text()
                title = title_text.strip().replace("\n", " ")
                button = week.locator(selectors.TEST_BTN)
                stat = misc.to_str(await week.locator(
                    selectors.TEST_WEEK_STAT).get_attribute("class"))
                if "done" not in stat:
                    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-info-processing-weekly-test") % title)
                    button.click()
                    await emulate_answer(page, **kwargs)
                    handled_page = True
                    break
            if not handled_page:
                next_btn = page.locator(selectors.TEST_NEXT_PAGE)
                logging.getLogger(core.APPID).warning(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-warning-no-test-on-current-page"))
                if await next_btn.get_attribute("aria-disabled") == "true":
                    logging.getLogger(core.APPID).error(lang.get_lang(
                        kwargs.get("lang", "zh-cn"), "core-error-no-available-test"))
                    skip = True
                    break
                elif await next_btn.get_attribute("aria-disabled") == "false":
                    await next_btn.click()
                    await page.locator(selectors.LOADING).wait_for(state="hidden")
                else:
                    break
            else:
                break
    elif page.url == urls.SPECIAL_EXAM_PAGE:
        while True:
            items = page.locator(selectors.TEST_ITEMS)
            await items.last.wait_for()
            handled_page = False
            for i in range(await items.count()):
                item = items.nth(i)
                points = item.locator(selectors.TEST_SPECIAL_POINTS)
                button = item.locator(selectors.TEST_BTN)
                title_element = item.locator(
                    selectors.TEST_SPECIAL_TITLE)
                before = await title_element.locator(
                    selectors.TEST_SPECIAL_TITLE_BEFORE).inner_text()
                after = await title_element.locator(
                    selectors.TEST_SPECIAL_TITLE_AFTER).inner_text()
                title_text = await title_element.inner_text()
                title = title_text.replace(
                    before, "").replace(after, "").strip().replace("\n", " ")
                if await points.count() == 0:
                    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-info-processing-special-test") % title)
                    await button.click()
                    await emulate_answer(page, **kwargs)
                    handled_page = True
                    break
            if not handled_page:
                next_btn = page.locator(selectors.TEST_NEXT_PAGE)
                logging.getLogger(core.APPID).warning(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-warning-no-test-on-current-page"))
                if await next_btn.get_attribute("aria-disabled") == "true":
                    logging.getLogger(core.APPID).error(lang.get_lang(
                        kwargs.get("lang", "zh-cn"), "core-error-no-available-test"))
                    skip = True
                    break
                elif await next_btn.get_attribute("aria-disabled") == "false":
                    next_btn.click()
                    await page.locator(selectors.LOADING).wait_for(state="hidden")
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
