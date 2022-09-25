import os
import time
import random
import base64
import aiohttp
import logging
import asyncio
from urllib.parse import urlparse
from autoxuexiplaywright.defines import core, urls, selectors, events
from autoxuexiplaywright.utils import misc, lang,  answerutils, storage, eventmanager
from playwright.async_api import Page, TimeoutError, async_playwright

__all__ = ["start"]
cache = set[str]()


def start(**kwargs) -> None:
    asyncio.run(run(**kwargs))


async def run(**kwargs) -> None:
    cache.clear()
    answerutils.init_sources(**kwargs)
    start_time = time.time()
    async with async_playwright() as p:
        browser = await p[kwargs.get("browser", "firefox")].launch(
            headless=not kwargs.get("debug", False), proxy=kwargs.get("proxy"),
            channel=kwargs.get("channel"), args=["--mute-audio"], devtools=not kwargs.get("debug", False),
            firefox_user_prefs={"media.volume_scale": "0.0"}, executable_path=kwargs.get("executable_path", None))
        if os.path.exists(storage.get_cache_path("cookies.json")):
            context = await browser.new_context(
                storage_state=storage.get_cache_path("cookies.json"))
        else:
            context = await browser.new_context()
        context.set_default_timeout(core.WAIT_PAGE_SECS*1000)
        try:
            await login(await context.new_page(), **kwargs)
            await check_status_and_finish(
                await context.new_page(),  **kwargs)
        except Exception as e:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-err-process-exception") % e)
        await context.close()
        await browser.close()
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


async def login(page: Page, **kwargs) -> None:
    eventmanager.find_event_by_id(events.EventId.STATUS_UPDATED).invoke(lang.get_lang(
        kwargs.get("lang", "zh-cn"), "ui-status-loging-in"))
    await page.bring_to_front()
    await page.goto(urls.LOGIN_PAGE)
    try:
        await page.locator(selectors.LOGIN_CHECK).wait_for(
            timeout=core.CHECK_ELEMENT_TIMEOUT_SECS*1000)
    except TimeoutError:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-failed"))
        failed_num = 0
        while True:
            qglogin = page.locator(selectors.LOGIN_QGLOGIN)
            try:
                await qglogin.scroll_into_view_if_needed()
            except TimeoutError:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-err-load-qr-failed"))
                raise RuntimeError()
            locator = qglogin.frame_locator(
                selectors.LOGIN_IFRAME).locator(selectors.LOGIN_IMAGE)
            img = base64.b64decode(misc.to_str(
                await locator.get_attribute("src")).split(",")[1])
            with open(storage.get_cache_path("qr.png"), "wb") as writer:
                writer.write(img)
            logging.getLogger(core.APPID).info(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-scan-required"))
            misc.img2shell(img, **kwargs)
            locator = page.locator(selectors.LOGIN_CHECK)
            try:
                await locator.wait_for()
            except TimeoutError as e:
                if failed_num > core.LOGIN_RETRY_TIMES:
                    logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-err-login-failed-too-many-times"))
                    raise e
                else:
                    failed_num += 1
                    await page.reload()
            else:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-qr-login-success"))
                break
    else:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-success"))
    await page.close()
    eventmanager.find_event_by_id(
        events.EventId.QR_UPDATED).invoke("".encode())
    await page.context.storage_state(
        path=storage.get_cache_path("cookies.json"))


async def check_status_and_finish(page: Page, **kwargs):
    process_position = 1  # login must be finished on app
    while True:
        await page.goto(urls.POINTS_PAGE)
        try:
            points = page.locator(selectors.POINTS_SPAN)
            for i in range(2):
                await points.nth(i).wait_for()
            points_ints = tuple([int(point.strip())
                                for point in await points.all_inner_texts()])
        except:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-update-score-failed"))
        else:
            logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-info-update-score-success") % points_ints)
            eventmanager.find_event_by_id(
                events.EventId.SCORE_UPDATED).invoke(points_ints)
        cards = page.locator(selectors.POINTS_CARDS)
        await cards.last.wait_for()
        login_task_style = misc.to_str(await cards.nth(0).locator(
            selectors.CARD_BUTTON).first.get_attribute("style"))
        if "not-allowed" not in login_task_style:
            logging.getLogger(core.APPID).warning(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-warning-login-task-not-completed"))
        if process_position < await cards.count():
            card = cards.nth(process_position)
            title = await card.locator(selectors.CARD_TITLE).first.inner_text()
            button = card.locator(selectors.CARD_BUTTON).first
            style = misc.to_str(await button.get_attribute("style"))
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
                eventmanager.find_event_by_id(events.EventId.STATUS_UPDATED).invoke(
                    lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "ui-status-tooltip") % title)
                try:
                    async with page.context.expect_page(timeout=core.WAIT_NEW_PAGE_SECS*1000) as page_event:
                        await button.click()
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
                if await pre_handle(target_page, close_page, process_type,  **kwargs):
                    process_position += 1
                await page.context.storage_state(
                    path=storage.get_cache_path("cookies.json"))
        else:
            break
    await page.close()


async def pre_handle(page: Page, close_page: bool, process_type: core.ProcessType,  **kwargs) -> bool:
    skip = True
    if process_type == core.ProcessType.NEWS:
        async with page.context.expect_page() as page_info:
            await page.locator(selectors.NEWS_TITLE_SPAN).click()
        value = await page_info.value
        skip = await handle_news(value, **kwargs)
        await value.close()
    elif process_type == core.ProcessType.VIDEO:
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
    elif process_type == core.ProcessType.TEST:
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


async def emulate_read(page: Page, **kwargs) -> None:
    read_all_paragraphs = True
    scroll_video_subtitle = True
    start_time = time.time()
    while True:
        if (time.time()-start_time) >= core.READ_TIME_SECS:
            break
        await page.wait_for_timeout(random.uniform(
            core.PROCESS_SLEEP_MIN, core.PROCESS_SLEEP_MAX)*1000)
        try:
            player = page.locator(selectors.VIDEO_PLAYER)
            if await player.count() > 0:
                await player.last.wait_for(timeout=core.READ_TIME_SECS*1000)
                play_btn = player.locator(selectors.PLAY_BTN)
                if "playing" not in misc.to_str(await play_btn.get_attribute("class")):
                    await play_btn.click(timeout=core.READ_TIME_SECS*1000)
        except:
            pass
        try:
            video_subtitle = page.locator(selectors.VIDEO_SUBTITLE)
            if await video_subtitle.count() > 0 and scroll_video_subtitle:
                await video_subtitle.first.scroll_into_view_if_needed()
                scroll_video_subtitle = False
            ps = page.locator(selectors.PAGE_PARAGRAPHS)
            if await ps.count() > 0:
                if read_all_paragraphs:
                    for i in range(await ps.count()):
                        await page.wait_for_timeout(random.uniform(
                            core.PROCESS_SLEEP_MIN, core.PROCESS_SLEEP_MAX)*1000)
                        await ps.nth(i).scroll_into_view_if_needed(
                            timeout=core.READ_TIME_SECS*1000)
                    read_all_paragraphs = False
                await ps.nth(random.randint(0, await ps.count()-1)
                             ).scroll_into_view_if_needed(timeout=core.READ_TIME_SECS*1000)
        except:
            pass


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


async def emulate_answer(page: Page,  **kwargs) -> None:
    while True:
        await AsyncQuestionItem(page, **kwargs).do_answer(**kwargs)
        result = page.locator(selectors.TEST_RESULT)
        try:
            await result.wait_for(timeout=core.WAIT_RESULT_SECS*1000)
        except TimeoutError:
            logging.getLogger(core.APPID).info(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-test-not-finish"))
        else:
            break


class AsyncQuestionItem():
    __all__ = ["do_answer"]

    def __init__(self, page: Page, **kwargs) -> None:
        asyncio.wait_for(self.__init(page, **kwargs))

    async def __init(self, page: Page, **kwargs):
        self.page = page
        question = self.page.locator(selectors.QUESTION)
        title_text = await question.locator(
            selectors.QUESTION_TITLE).inner_text()
        self.title = title_text.strip().replace("\n", " ")
        logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-info-current-question-title") % self.title)
        self.tips = self.title
        answers = question.locator(selectors.ANSWERS)
        if await answers.count() == 1:
            self.answer_items = answers.locator(selectors.ANSWER_ITEM)
            self.question_type = answerutils.QuestionType.CHOICE
            self.tips += "\n"+lang.get_lang(kwargs.get("lang", "zh-cn"), "core-available-answers") + \
                core.ANSWER_CONNECTOR.join(
                    [item.strip() for item in await self.answer_items.all_inner_texts()])
            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-debug-current-question-type-choice"))
        elif await answers.count() == 0:
            self.answer_items = question.locator(selectors.BLANK)
            self.question_type = answerutils.QuestionType.BLANK
            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-debug-current-question-type-blank"))
        else:
            self.answer_items = None
            self.question_type = answerutils.QuestionType.UNKNOWN

    async def do_answer(self, **kwargs) -> None:
        if self.answer_items is None:
            return
        manual_input = False
        answer = answerutils.get_answer_from_sources(self.title, **kwargs)
        if answer == []:
            answer = await self.try_find_answer_from_page(**kwargs)
        answer = [answer_item.strip(
        ) for answer_item in answer if answerutils.is_valid_answer(answer_item.strip())]
        logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-final-answer-list") % answer)
        if answer == []:
            self.try_get_video(**kwargs)
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-no-answer-found"))
            answer = answerutils.request_answer(self.tips, **kwargs)
        if answer == []:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-no-answer-even-tried-manual-input"))
        else:
            manual_input = True
        answer_items_count = await self.answer_items.count(
        ) if self.answer_items is not None else 0
        answer_count = len(answer)
        logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-answer-items-count-and-answers-count") % (answer_items_count, answer_count))
        if answer_count > 0:
            if answer_count < answer_items_count:
                # normal status
                operated = False
                while not operated:
                    answer_start_pos = 0
                    if answer_start_pos <= answer_items_count:
                        for answer_str in answer:
                            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                                "lang", "zh-cn"), "core-debug-current-answer-text") % answer_str)
                            for j in range(answer_start_pos, answer_items_count):
                                if self.question_type == answerutils.QuestionType.CHOICE:
                                    current_choice = self.answer_items.nth(j)
                                    class_str = misc.to_str(
                                        await current_choice.get_attribute("class"))
                                    text = await current_choice.inner_text()
                                    text_str = text.strip()
                                    logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                                        "lang", "zh-cn"), "core-debug-current-choice-class") % class_str)
                                    logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                                        "lang", "zh-cn"), "core-debug-current-choice-text") % text_str)
                                    if (answer_str in text_str) and ("chosen" not in class_str):
                                        await current_choice.click(delay=random.uniform(
                                            core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                                        operated = True
                                elif self.question_type == answerutils.QuestionType.BLANK:
                                    await self.answer_items.nth(j).type(answer_str, delay=random.uniform(
                                        core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                                    operated = True
                                if operated:
                                    answer_start_pos = j+1
                                    break
                        if not operated:
                            # answer on webpage is not correct, input nothing to skip
                            answer = answerutils.request_answer(
                                self.tips, **kwargs)
                            if answer == []:
                                await self.random_finish(**kwargs)
                                operated = True
                            else:
                                manual_input = True
                    else:
                        # force break loop
                        operated = True
            else:
                # should choose all
                for i in range(answer_items_count):
                    if self.question_type == answerutils.QuestionType.CHOICE:
                        await self.answer_items.nth(i).click(delay=random.uniform(
                            core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                    elif self.question_type == answerutils.QuestionType.BLANK:
                        await self.answer_items.nth(i).type(answer[i], delay=random.uniform(
                            core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            # no answer, random finish
            await self.random_finish(**kwargs)
        # submit answer or finish test
        action_row = self.page.locator(selectors.TEST_ACTION_ROW)
        next_btn = action_row.locator(selectors.TEST_NEXT_QUESTION_BTN)
        if await next_btn.is_enabled():
            await next_btn.click(delay=random.uniform(
                core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            await action_row.locator(selectors.TEST_SUBMIT_BTN).click(delay=random.uniform(
                core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        if await self.page.locator(selectors.TEST_SOLUTION).count() > 0:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-answer-is-wrong") % self.title)
            await next_btn.click(delay=random.uniform(
                core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        elif (answer != []) and manual_input:
            answerutils.add_answer(self.title, answer)

    async def try_find_answer_from_page(self, **kwargs) -> list[str]:
        answer = []
        tips = self.page.locator(
            selectors.QUESTION).locator(selectors.TIPS)
        if "ant-popover-open" not in misc.to_str(await tips.get_attribute("class")):
            await tips.click()
        popover = self.page.locator(selectors.POPOVER)
        if "ant-popover-hidden" not in misc.to_str(await popover.get_attribute("class")):
            font = popover.locator(selectors.ANSWER_FONT)
            if await font.count() > 0:
                await font.last.wait_for()
                answer = [text.strip() for text in await font.all_inner_texts()]
                self.tips += "\n"+lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-available-tips")+core.ANSWER_CONNECTOR.join(answer)
                logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-debug-raw-answer-list") % answer)
        if "ant-popover-open" in misc.to_str(await tips.get_attribute("class")):
            await tips.click()
        return answer

    async def try_get_video(self, **kwargs) -> None:
        async def get_video_by_address(address: str, headers: dict | None = None) -> bytes:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(address) as response:
                    return await response.content.read()
        video_player = self.page.locator(selectors.TEST_VIDEO_PLAYER)
        if await video_player.count() > 0:
            for i in range(await video_player.count()):
                await video_player.nth(i).hover()
                try:
                    async with self.page.expect_response(core.VIDEO_REQUEST_REGEX) as response_info:
                        await video_player.nth(i).locator(
                            selectors.TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-error-test-download-video-failed"))
                else:
                    try:
                        value = await response_info.value
                        if value.url.endswith(".mp4"):
                            with open(storage.get_cache_path("video.mp4"), "wb") as writer:
                                writer.write(await value.body())
                        elif value.url.endswith(".m3u8"):
                            url = urlparse(value.url)
                            prefix = "%s://%s/" % (url.scheme, url.netloc +
                                                   "/".join(url.path.split("/")[:-1]))
                            value_text = await value.text()
                            jobs = []
                            for line in value_text.split("\n"):
                                if not line.startswith("#"):
                                    jobs.append(prefix+line)
                            results = bytes.join(asyncio.gather([get_video_by_address(line, await value.request.all_headers()) for line in jobs]))
                            with open("video.mp4", "wb") as writer:
                                writer.write(results)
                    except:
                        logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                            "lang", "zh-cn"), "core-error-test-download-video-failed"))
                    else:
                        logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                            "lang", "zh-cn"), "core-info-test-download-video-success"))

    async def random_finish(self, **kwargs) -> None:
        logging.getLogger(core.APPID).error(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-error-use-random-answer"))
        if self.answer_items is not None:
            for i in range(await self.answer_items.count()):
                if self.question_type == answerutils.QuestionType.CHOICE:
                    await self.answer_items.nth(i).click(delay=random.uniform(
                        core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                elif self.question_type == answerutils.QuestionType.BLANK:
                    await self.answer_items.nth(i).type(answerutils.gen_random_str(), delay=random.uniform(
                        core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
