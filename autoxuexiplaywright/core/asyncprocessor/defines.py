import random
import asyncio
import logging
import aiohttp
from urllib.parse import urlparse
from playwright.async_api import Page
from autoxuexiplaywright.defines import selectors, core
from autoxuexiplaywright.utils import answerutils, lang, misc, storage
from autoxuexiplaywright.core.asyncprocessor.captchautils import try_finish_captcha

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
        captcha = self.page.locator(selectors.TEST_CAPTCHA_SWIPER)
        if captcha.count() > 0:
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-captcha-found"))
            await try_finish_captcha(captcha)
        elif await self.page.locator(selectors.TEST_SOLUTION).count() > 0:
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
