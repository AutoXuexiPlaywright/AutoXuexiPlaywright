from logging import getLogger
from random import uniform
from requests import get
from urllib.parse import urlparse
from playwright.sync_api import Page, TimeoutError

from autoxuexiplaywright.defines.core import (
    APPID, ANSWER_CONNECTOR, ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS, VIDEO_REQUEST_REGEX
)
from autoxuexiplaywright.defines.selectors import (
    QUESTION, QUESTION_TITLE, ANSWERS, ANSWER_ITEM, BLANK, TEST_ACTION_ROW, TEST_NEXT_QUESTION_BTN,
    TEST_SUBMIT_BTN, TEST_CAPTCHA_SWIPER, TEST_CAPTCHA_TEXT, TEST_SOLUTION, TIPS, POPOVER, ANSWER_FONT,
    TEST_VIDEO_PLAYER, TEST_VIDEO_PLAY_BTN
)
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.answerutils import (
    QuestionType, get_answer_from_sources, is_valid_answer, request_answer, add_answer, gen_random_str
)
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.core.syncprocessor.captchautils import try_finish_captcha


class SyncQuestionItem():
    __all__ = ["do_answer"]

    def __init__(self, page: Page, **kwargs) -> None:
        self.page = page
        self.kwargs = kwargs

    def __enter__(self):
        question = self.page.locator(QUESTION)
        self.title = question.locator(
            QUESTION_TITLE).inner_text().strip().replace("\n", " ")
        getLogger(APPID).info(get_lang(self.kwargs.get(
            "lang", "zh-cn"), "core-info-current-question-title") % self.title)
        self.tips = self.title
        answers = question.locator(ANSWERS)
        if answers.count() == 1:
            self.answer_items = answers.locator(ANSWER_ITEM)
            self.question_type = QuestionType.CHOICE
            self.tips += "\n"+get_lang(self.kwargs.get("lang", "zh-cn"), "core-available-answers") + \
                ANSWER_CONNECTOR.join(
                    [item.strip() for item in self.answer_items.all_inner_texts()])
            getLogger(APPID).debug(get_lang(self.kwargs.get(
                "lang", "zh-cn"), "core-debug-current-question-type-choice"))
        elif answers.count() == 0:
            self.answer_items = question.locator(BLANK)
            self.question_type = QuestionType.BLANK
            getLogger(APPID).debug(get_lang(self.kwargs.get(
                "lang", "zh-cn"), "core-debug-current-question-type-blank"))
        else:
            self.answer_items = None
            self.question_type = QuestionType.UNKNOWN
        return self

    def __exit__(self, *args):
        pass

    def do_answer(self, **kwargs) -> None:
        if self.answer_items is None:
            return
        manual_input = False
        answer = get_answer_from_sources(self.title, **kwargs)
        if answer == []:
            answer = self.try_find_answer_from_page(**kwargs)
        answer = [answer_item.strip(
        ) for answer_item in answer if is_valid_answer(answer_item.strip())]
        getLogger(APPID).debug(get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-final-answer-list") % answer)
        if answer == []:
            self.try_get_video(**kwargs)
            getLogger(APPID).error(get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-no-answer-found"))
            answer = request_answer(self.tips, **kwargs)
        if answer == []:
            getLogger(APPID).error(get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-no-answer-even-tried-manual-input"))
        else:
            manual_input = True
        answer_items_count = self.answer_items.count(
        ) if self.answer_items is not None else 0
        answer_count = len(answer)
        getLogger(APPID).debug(get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-answer-items-count-and-answers-count") % (answer_items_count, answer_count))
        if answer_count > 0:
            if answer_count < answer_items_count:
                # normal status
                operated = False
                while not operated:
                    answer_start_pos = 0
                    if answer_start_pos <= answer_items_count:
                        for answer_str in answer:
                            getLogger(APPID).debug(get_lang(kwargs.get(
                                "lang", "zh-cn"), "core-debug-current-answer-text") % answer_str)
                            for j in range(answer_start_pos, answer_items_count):
                                if self.question_type == QuestionType.CHOICE:
                                    current_choice = self.answer_items.nth(j)
                                    class_str = to_str(
                                        current_choice.get_attribute("class"))
                                    text_str = current_choice.inner_text().strip()
                                    getLogger(APPID).debug(get_lang(kwargs.get(
                                        "lang", "zh-cn"), "core-debug-current-choice-class") % class_str)
                                    getLogger(APPID).debug(get_lang(kwargs.get(
                                        "lang", "zh-cn"), "core-debug-current-choice-text") % text_str)
                                    if (answer_str in text_str) and ("chosen" not in class_str):
                                        current_choice.click(delay=uniform(
                                            ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                                        operated = True
                                elif self.question_type == QuestionType.BLANK:
                                    self.answer_items.nth(j).type(answer_str, delay=uniform(
                                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                                    operated = True
                                if operated:
                                    answer_start_pos = j+1
                                    break
                        if not operated:
                            # answer on webpage is not correct, input nothing to skip
                            answer = request_answer(
                                self.tips, **kwargs)
                            if answer == []:
                                self.random_finish(**kwargs)
                                operated = True
                            else:
                                manual_input = True
                    else:
                        # force break loop
                        operated = True
            else:
                # should choose all
                for i in range(answer_items_count):
                    if self.question_type == QuestionType.CHOICE:
                        self.answer_items.nth(i).click(delay=uniform(
                            ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                    elif self.question_type == QuestionType.BLANK:
                        self.answer_items.nth(i).type(answer[i], delay=uniform(
                            ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            # no answer, random finish
            self.random_finish(**kwargs)
        # submit answer or finish test
        action_row = self.page.locator(TEST_ACTION_ROW)
        next_btn = action_row.locator(TEST_NEXT_QUESTION_BTN)
        if next_btn.is_enabled():
            next_btn.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            action_row.locator(TEST_SUBMIT_BTN).click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        captcha = self.page.locator(TEST_CAPTCHA_SWIPER)
        if captcha.locator(TEST_CAPTCHA_TEXT).count() > 0:
            getLogger(APPID).warning(get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-captcha-found"))
            try_finish_captcha(captcha)
        if self.page.locator(TEST_SOLUTION).count() > 0:
            getLogger(APPID).error(get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-answer-is-wrong") % self.title)
            next_btn.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        elif (answer != []) and manual_input:
            add_answer(self.title, answer)

    def try_find_answer_from_page(self, **kwargs) -> list[str]:
        answer = []
        tips = self.page.locator(
            QUESTION).locator(TIPS)
        if "ant-popover-open" not in to_str(tips.get_attribute("class")):
            tips.click()
        popover = self.page.locator(POPOVER)
        if "ant-popover-hidden" not in to_str(popover.get_attribute("class")):
            font = popover.locator(ANSWER_FONT)
            if font.count() > 0:
                font.last.wait_for()
                answer = [text.strip() for text in font.all_inner_texts()]
                self.tips += "\n"+get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-available-tips")+ANSWER_CONNECTOR.join(answer)
                getLogger(APPID).debug(get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-debug-raw-answer-list") % answer)
        if "ant-popover-open" in to_str(tips.get_attribute("class")):
            tips.click()
        return answer

    def try_get_video(self, **kwargs) -> None:
        video_player = self.page.locator(TEST_VIDEO_PLAYER)
        if video_player.count() > 0:
            for i in range(video_player.count()):
                video_player.nth(i).hover()
                try:
                    with self.page.expect_response(VIDEO_REQUEST_REGEX) as response_info:
                        video_player.nth(i).locator(
                            TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    getLogger(APPID).error(get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-error-test-download-video-failed"))
                else:
                    try:
                        if response_info.value.url.endswith(".mp4"):
                            with open(get_cache_path("video.mp4"), "wb") as writer:
                                writer.write(response_info.value.body())
                        elif response_info.value.url.endswith(".m3u8"):
                            url = urlparse(response_info.value.url)
                            prefix = "%s://%s/" % (url.scheme, url.netloc +
                                                   "/".join(url.path.split("/")[:-1]))
                            for line in response_info.value.text().split("\n"):
                                if not line.startswith("#"):
                                    with open(get_cache_path("video.mp4"), "ab") as writer:
                                        writer.write(get(
                                            url=prefix+line, headers=response_info.value.request.all_headers()).content)
                    except:
                        getLogger(APPID).error(get_lang(kwargs.get(
                            "lang", "zh-cn"), "core-error-test-download-video-failed"))
                    else:
                        getLogger(APPID).info(get_lang(kwargs.get(
                            "lang", "zh-cn"), "core-info-test-download-video-success"))

    def random_finish(self, **kwargs) -> None:
        getLogger(APPID).error(get_lang(
            kwargs.get("lang", "zh-cn"), "core-error-use-random-answer"))
        if self.answer_items is not None:
            for i in range(self.answer_items.count()):
                if self.question_type == QuestionType.CHOICE:
                    self.answer_items.nth(i).click(delay=uniform(
                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                elif self.question_type == QuestionType.BLANK:
                    self.answer_items.nth(i).type(gen_random_str(), delay=uniform(
                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)


__all__ = ["SyncQuestionItem"]
