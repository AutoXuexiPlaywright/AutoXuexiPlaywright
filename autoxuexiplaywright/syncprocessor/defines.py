from logging import getLogger
from random import uniform
from requests import get
from urllib.parse import urlparse
from playwright.sync_api import Page, TimeoutError

from autoxuexiplaywright.defines.core import (
    ANSWER_CONNECTOR, ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS, VIDEO_REQUEST_REGEX
)
from autoxuexiplaywright.defines.selectors import AnswerSelectors
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.answerutils import (
    QuestionType, get_answer_from_sources, is_valid_answer, request_answer, add_answer, gen_random_str
)
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.syncprocessor.captchautils import try_finish_captcha

from autoxuexiplaywright import appid


class SyncQuestionItem():
    __all__ = ["do_answer"]

    def __init__(self, page: Page) -> None:
        self.page = page
        self.config = Config.get_instance()

    def __enter__(self):
        question = self.page.locator(AnswerSelectors.QUESTION)
        self.title = question.locator(
            AnswerSelectors.QUESTION_TITLE).inner_text().strip().replace("\n", " ")
        getLogger(appid).info(
            get_lang(self.config.lang, "core-info-current-question-title") % self.title)
        self.tips = self.title
        answers = question.locator(AnswerSelectors.ANSWERS)
        if answers.count() == 1:
            self.answer_items = answers.locator(AnswerSelectors.ANSWER_ITEM)
            self.question_type = QuestionType.CHOICE
            self.tips += "\n"+get_lang(self.config.lang, "core-available-answers") + \
                ANSWER_CONNECTOR.join(
                    [item.strip() for item in self.answer_items.all_inner_texts()])
            getLogger(appid).debug(
                get_lang(self.config.lang, "core-debug-current-question-type-choice"))
        elif answers.count() == 0:
            self.answer_items = question.locator(AnswerSelectors.BLANK)
            self.question_type = QuestionType.BLANK
            getLogger(appid).debug(
                get_lang(self.config.lang, "core-debug-current-question-type-blank"))
        else:
            self.answer_items = None
            self.question_type = QuestionType.UNKNOWN
        return self

    def __exit__(self, *args: ...):
        pass

    def do_answer(self) -> None:
        if self.answer_items is None:
            return
        manual_input = False
        answer = get_answer_from_sources(self.title)
        if answer == []:
            answer = self.try_find_answer_from_page()
        answer = [answer_item.strip(
        ) for answer_item in answer if is_valid_answer(answer_item.strip())]
        getLogger(appid).debug(
            get_lang(self.config.lang, "core-debug-final-answer-list") % answer)
        if answer == []:
            self.try_get_video()
            getLogger(appid).error(get_lang(
                self.config.lang, "core-error-no-answer-found"))
            answer = request_answer(self.tips)
        if answer == []:
            getLogger(appid).error(get_lang(
                self.config.lang, "core-error-no-answer-even-tried-manual-input"))
        else:
            manual_input = True
        answer_items_count = self.answer_items.count(
        ) if self.answer_items is not None else 0
        answer_count = len(answer)
        getLogger(appid).debug(get_lang(
            self.config.lang, "core-debug-answer-items-count-and-answers-count") % (answer_items_count, answer_count))
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
                                        current_choice.get_attribute("class"))
                                    text_str = current_choice.inner_text().strip()
                                    getLogger(appid).debug(
                                        get_lang(self.config.lang, "core-debug-current-choice-class") % class_str)
                                    getLogger(appid).debug(
                                        get_lang(self.config.lang, "core-debug-current-choice-text") % text_str)
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
                                self.tips)
                            if answer == []:
                                self.random_finish()
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
                            self.answer_items.nth(i).click(delay=uniform(
                                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                        case QuestionType.BLANK:
                            self.answer_items.nth(i).type(answer[i], delay=uniform(
                                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                        case QuestionType.UNKNOWN:
                            getLogger(appid).error(
                                get_lang(self.config.lang, "core-error-unknown-answer-type"))
        else:
            # no answer, random finish
            self.random_finish()
        # submit answer or finish test
        action_row = self.page.locator(AnswerSelectors.TEST_ACTION_ROW)
        next_btn = action_row.locator(AnswerSelectors.TEST_NEXT_QUESTION_BTN)
        if next_btn.is_enabled():
            next_btn.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            action_row.locator(AnswerSelectors.TEST_SUBMIT_BTN).click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        captcha = self.page.locator(AnswerSelectors.TEST_CAPTCHA_SWIPER)
        if captcha.locator(AnswerSelectors.TEST_CAPTCHA_TEXT).count() > 0:
            getLogger(appid).warning(get_lang(
                self.config.lang, "core-warning-captcha-found"))
            try_finish_captcha(captcha)
        if self.page.locator(AnswerSelectors.TEST_SOLUTION).count() > 0:
            getLogger(appid).error(get_lang(
                self.config.lang, "core-error-answer-is-wrong") % self.title)
            next_btn.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        elif (answer != []) and manual_input:
            add_answer(self.title, answer)

    def try_find_answer_from_page(self) -> list[str]:
        config = Config.get_instance()
        answer = []
        tips = self.page.locator(
            AnswerSelectors.QUESTION).locator(AnswerSelectors.TIPS)
        if "ant-popover-open" not in to_str(tips.get_attribute("class")):
            tips.click()
        popover = self.page.locator(AnswerSelectors.POPOVER)
        if "ant-popover-hidden" not in to_str(popover.get_attribute("class")):
            font = popover.locator(AnswerSelectors.ANSWER_FONT)
            if font.count() > 0:
                font.last.wait_for()
                answer = [text.strip() for text in font.all_inner_texts()]
                self.tips += "\n" + \
                    get_lang(config.lang, "core-available-tips") + \
                    ANSWER_CONNECTOR.join(answer)
                getLogger(appid).debug(
                    get_lang(config.lang, "core-debug-raw-answer-list") % answer)
        if "ant-popover-open" in to_str(tips.get_attribute("class")):
            tips.click()
        return answer

    def try_get_video(self) -> None:
        config = Config.get_instance()
        video_player = self.page.locator(AnswerSelectors.TEST_VIDEO_PLAYER)
        if video_player.count() > 0:
            for i in range(video_player.count()):
                video_player.nth(i).hover()
                try:
                    with self.page.expect_response(VIDEO_REQUEST_REGEX) as response_info:
                        video_player.nth(i).locator(
                            AnswerSelectors.TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    getLogger(appid).error(
                        get_lang(config.lang, "core-error-test-download-video-failed"))
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
                        getLogger(appid).error(
                            get_lang(config.lang, "core-error-test-download-video-failed"))
                    else:
                        getLogger(appid).info(
                            get_lang(config.lang, "core-info-test-download-video-success"))

    def random_finish(self) -> None:
        getLogger(appid).error(get_lang(
            Config.get_instance().lang, "core-error-use-random-answer"))
        if self.answer_items is not None:
            for i in range(self.answer_items.count()):
                if self.question_type == QuestionType.CHOICE:
                    self.answer_items.nth(i).click(delay=uniform(
                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
                elif self.question_type == QuestionType.BLANK:
                    self.answer_items.nth(i).type(gen_random_str(), delay=uniform(
                        ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)


__all__ = ["SyncQuestionItem"]
