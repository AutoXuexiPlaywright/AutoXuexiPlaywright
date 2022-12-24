from random import uniform
from asyncio import gather
from logging import getLogger
from aiohttp import ClientSession
from urllib.parse import urlparse
from playwright.async_api import Page, TimeoutError

from autoxuexiplaywright.defines.core import (
    ANSWER_CONNECTOR, ANSWER_SLEEP_MIN_SECS,
    ANSWER_SLEEP_MAX_SECS, VIDEO_REQUEST_REGEX)
from autoxuexiplaywright.defines.selectors import AnswerSelectors
from autoxuexiplaywright.utils.answerutils import (
    QuestionType, get_answer_from_sources, request_answer, add_answer, gen_random_str, is_valid_answer)
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.asyncprocessor.captchautils import try_finish_captcha

from autoxuexiplaywright import appid


class AsyncQuestionItem():
    __all__ = ["do_answer"]

    def __init__(self, page: Page) -> None:
        self.page = page
        self.config = Config.get_instance()

    async def __aenter__(self):
        question = self.page.locator(AnswerSelectors.QUESTION)
        title_text = await question.locator(
            AnswerSelectors.QUESTION_TITLE).inner_text()
        self.title = title_text.strip().replace("\n", " ")
        getLogger(appid).info(
            get_lang(self.config.lang, "core-info-current-question-title") % self.title)
        self.tips = self.title
        answers = question.locator(AnswerSelectors.ANSWERS)
        if await answers.count() == 1:
            self.answer_items = answers.locator(AnswerSelectors.ANSWER_ITEM)
            self.question_type = QuestionType.CHOICE
            self.tips += "\n"+get_lang(self.config.lang, "core-available-answers") + \
                ANSWER_CONNECTOR.join(
                    [item.strip() for item in await self.answer_items.all_inner_texts()])
            getLogger(appid).debug(
                get_lang(self.config.lang, "core-debug-current-question-type-choice"))
        elif await answers.count() == 0:
            self.answer_items = question.locator(AnswerSelectors.BLANK)
            self.question_type = QuestionType.BLANK
            getLogger(appid).debug(
                get_lang(self.config.lang, "core-debug-current-question-type-blank"))
        else:
            self.answer_items = None
            self.question_type = QuestionType.UNKNOWN
        return self

    async def __aexit__(self, *args: ...):
        pass

    async def do_answer(self) -> None:
        if self.answer_items is None:
            return
        manual_input = False
        answer = get_answer_from_sources(self.title)
        if answer == []:
            answer = await self.try_find_answer_from_page()
        answer = [answer_item.strip(
        ) for answer_item in answer if is_valid_answer(answer_item.strip())]
        getLogger(appid).debug(get_lang(self.config.lang,
                                        "core-debug-final-answer-list") % answer)
        if answer == []:
            await self.try_get_video()
            getLogger(appid).error(get_lang(
                self.config.lang, "core-error-no-answer-found"))
            answer = request_answer(self.tips)
        if answer == []:
            getLogger(appid).error(get_lang(
                self.config.lang, "core-error-no-answer-even-tried-manual-input"))
        else:
            manual_input = True
        answer_items_count = await self.answer_items.count(
        ) if self.answer_items is not None else 0
        answer_count = len(answer)
        getLogger(appid).debug(get_lang(self.config.lang,
                                        "core-debug-answer-items-count-and-answers-count") % (answer_items_count, answer_count))
        if answer_count > 0:
            if answer_count < answer_items_count:
                # normal status
                operated = False
                while not operated:
                    answer_start_pos = 0
                    if answer_start_pos <= answer_items_count:
                        for answer_str in answer:
                            getLogger(appid).debug(
                                get_lang(self.config.lang, "core-debug-current-answer-text") % answer_str)
                            for j in range(answer_start_pos, answer_items_count):
                                if self.question_type == QuestionType.CHOICE:
                                    current_choice = self.answer_items.nth(j)
                                    class_str = to_str(
                                        await current_choice.get_attribute("class"))
                                    text = await current_choice.inner_text()
                                    text_str = text.strip()
                                    getLogger(appid).debug(
                                        get_lang(self.config.lang, "core-debug-current-choice-class") % class_str)
                                    getLogger(appid).debug(
                                        get_lang(self.config.lang, "core-debug-current-choice-text") % text_str)
                                    if (answer_str in text_str) and ("chosen" not in class_str):
                                        await current_choice.click(delay=uniform(
                                            ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                                        operated = True
                                elif self.question_type == QuestionType.BLANK:
                                    await self.answer_items.nth(j).type(answer_str, delay=uniform(
                                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                                    operated = True
                                if operated:
                                    answer_start_pos = j+1
                                    break
                        if not operated:
                            # answer on webpage is not correct, input nothing to skip
                            answer = request_answer(
                                self.tips)
                            if answer == []:
                                await self.random_finish()
                                operated = True
                            else:
                                manual_input = True
                    else:
                        # force break loop
                        operated = True
            else:
                # should choose all
                for i in range(answer_items_count):
                    match self.question_type:
                        case QuestionType.CHOICE:
                            await self.answer_items.nth(i).click(delay=uniform(
                                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                        case QuestionType.BLANK:
                            await self.answer_items.nth(i).type(answer[i], delay=uniform(
                                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                        case QuestionType.UNKNOWN:
                            getLogger(appid).error(
                                get_lang(self.config.lang, "core-error-unknown-answer-type"))
        else:
            # no answer, random finish
            await self.random_finish()
        # submit answer or finish test
        action_row = self.page.locator(AnswerSelectors.TEST_ACTION_ROW)
        next_btn = action_row.locator(AnswerSelectors.TEST_NEXT_QUESTION_BTN)
        if await next_btn.is_enabled():
            await next_btn.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            await action_row.locator(AnswerSelectors.TEST_SUBMIT_BTN).click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        captcha = self.page.locator(AnswerSelectors.TEST_CAPTCHA_SWIPER)
        if await captcha.locator(AnswerSelectors.TEST_CAPTCHA_TEXT).count() > 0:
            getLogger(appid).warning(get_lang(
                self.config.lang, "core-warning-captcha-found"))
            await try_finish_captcha(captcha)
        if await self.page.locator(AnswerSelectors.TEST_SOLUTION).count() > 0:
            getLogger(appid).error(get_lang(
                self.config.lang, "core-error-answer-is-wrong") % self.title)
            await next_btn.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        elif (answer != []) and manual_input:
            add_answer(self.title, answer)

    async def try_find_answer_from_page(self) -> list[str]:
        answer = []
        tips = self.page.locator(
            AnswerSelectors.QUESTION).locator(AnswerSelectors.TIPS)
        if "ant-popover-open" not in to_str(await tips.get_attribute("class")):
            await tips.click()
        popover = self.page.locator(AnswerSelectors.POPOVER)
        if "ant-popover-hidden" not in to_str(await popover.get_attribute("class")):
            font = popover.locator(AnswerSelectors.ANSWER_FONT)
            if await font.count() > 0:
                await font.last.wait_for()
                answer = [text.strip() for text in await font.all_inner_texts()]
                self.tips += "\n" + \
                    get_lang(self.config.lang, "core-available-tips") + \
                    ANSWER_CONNECTOR.join(answer)
                getLogger(appid).debug(get_lang(self.config.lang,
                                                "core-debug-raw-answer-list") % answer)
        if "ant-popover-open" in to_str(await tips.get_attribute("class")):
            await tips.click()
        return answer

    async def try_get_video(self) -> None:
        async def get_video_by_address(address: str, headers: dict[str, str] | None = None) -> bytes:
            async with ClientSession(headers=headers) as session:
                async with session.get(address) as response:
                    return await response.content.read()
        video_player = self.page.locator(AnswerSelectors.TEST_VIDEO_PLAYER)
        if await video_player.count() > 0:
            for i in range(await video_player.count()):
                await video_player.nth(i).hover()
                try:
                    async with self.page.expect_response(VIDEO_REQUEST_REGEX) as response_info:
                        await video_player.nth(i).locator(
                            AnswerSelectors.TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    getLogger(appid).error(get_lang(self.config.lang,
                                                    "core-error-test-download-video-failed"))
                else:
                    try:
                        value = await response_info.value
                        if value.url.endswith(".mp4"):
                            with open(get_cache_path("video.mp4"), "wb") as writer:
                                writer.write(await value.body())
                        elif value.url.endswith(".m3u8"):
                            url = urlparse(value.url)
                            prefix = "%s://%s/" % (url.scheme, url.netloc +
                                                   "/".join(url.path.split("/")[:-1]))
                            value_text = await value.text()
                            jobs: list[str] = []
                            for line in value_text.split("\n"):
                                if not line.startswith("#"):
                                    jobs.append(prefix+line)
                            cors = [get_video_by_address(line, await value.request.all_headers()) for line in jobs]
                            results = bytes().join(await gather(*cors))
                            with open("video.mp4", "wb") as writer:
                                writer.write(results)
                    except:
                        getLogger(appid).error(
                            get_lang(self.config.lang, "core-error-test-download-video-failed"))
                    else:
                        getLogger(appid).info(
                            get_lang(self.config.lang, "core-info-test-download-video-success"))

    async def random_finish(self) -> None:
        getLogger(appid).error(get_lang(
            self.config.lang, "core-error-use-random-answer"))
        if self.answer_items is not None:
            for i in range(await self.answer_items.count()):
                if self.question_type == QuestionType.CHOICE:
                    await self.answer_items.nth(i).click(delay=uniform(
                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                elif self.question_type == QuestionType.BLANK:
                    await self.answer_items.nth(i).type(gen_random_str(), delay=uniform(
                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
