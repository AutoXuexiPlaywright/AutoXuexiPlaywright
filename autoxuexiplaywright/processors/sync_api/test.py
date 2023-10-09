from time import sleep
from random import randint, uniform
from queue import Queue
from urllib.parse import urlparse
from playwright.sync_api import Locator, TimeoutError
# Relative imports
from .task import Task, TaskStatus
from ..common import WAIT_RESULT_SECS, WAIT_CHOICE_SECS, ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS, VIDEO_REQUEST_REGEX, ANSWER_CONNECTOR, clean_string
from ..common.answer.utils import is_valid_answer, gen_random_string
from ..common.answer.sources import add_answer_to_all_sources, find_answer_in_answer_sources
from ..common.urls import DAILY_EXAM_PAGE, WEEKLY_EXAM_PAGE, SPECIAL_EXAM_PAGE
from ..common.selectors import Selectors, TestSelectors
from ...languages import get_language_string
from ...logger import info, debug, error, warning
from ...config import get_runtime_config
from ...events import EventID, find_event_by_id
from ...storage import get_cache_path


_config = get_runtime_config()


class _TestTask(Task):
    @property
    def requires(self) -> list[str]:
        return ["登录"]

    def finish(self) -> bool:
        while not self._is_test_finished():
            # Get question title and choice(s) or title only
            question = self.last_page.locator(TestSelectors.QUESTION).last
            question.scroll_into_view_if_needed()
            choices = question.locator(TestSelectors.ANSWERS)
            self._wait_locator(choices.last, WAIT_CHOICE_SECS * 1000)
            title_element = question.locator(TestSelectors.QUESTION_TITLE).last
            title_element.scroll_into_view_if_needed()
            title = clean_string(title_element.inner_text())
            info(get_language_string("core-info-current-question-title") % title)
            tips = [title]
            match choices.count():
                case 0:
                    # Blank
                    items_to_answer = question.locator(
                        TestSelectors.BLANK)
                    debug(get_language_string(
                        "core-debug-current-question-type-blank"))
                case 1:
                    # Choice
                    items_to_answer = choices.locator(
                        TestSelectors.ANSWER_ITEM)
                    tips.append(get_language_string("core-available-answers") +
                                ANSWER_CONNECTOR.join(
                        [clean_string(item) for item in items_to_answer.all_inner_texts()])
                    )
                    debug(get_language_string(
                        "core-debug-current-question-type-choice"))
                case _:
                    self.status = TaskStatus.FAILED
                    return False
            if not self._do_answer(items_to_answer, choices.count() == 0, tips):
                error(get_language_string("core-error-answer-failed"))
            self._go_to_next_question()
            if self.last_page.locator(TestSelectors.TEST_SOLUTION).count() > 0:
                error(get_language_string("core-error-answer-is-wrong") % title)
                self._go_to_next_question()
        return True

    def _get_answer_from_page(self) -> list[str]:
        answer_on_page: list[str] = []
        tips = self.last_page.locator(
            TestSelectors.QUESTION).locator(TestSelectors.TIPS)
        if "ant-popover-open" not in (tips.get_attribute("class") or ""):
            tips.click()
        popover = self.last_page.locator(TestSelectors.POPOVER)
        if "ant-popover-hidden" not in (popover.get_attribute("class") or ""):
            font = popover.locator(TestSelectors.ANSWER_FONT)
            self._wait_locator(font.last)
            if font.count() > 0:
                answer_on_page_raw = [clean_string(text)
                                      for text in font.all_inner_texts()]
                for answer in answer_on_page_raw:
                    if is_valid_answer(answer):
                        answer_on_page.append(answer)
        if "ant-popover-open" in (tips.get_attribute("class") or ""):
            tips.click()
        debug(get_language_string("core-debug-raw-answer-list") % answer_on_page)
        return answer_on_page

    def _get_answer_from_manual_input(self, tips: list[str]) -> list[str]:
        if _config.get_video:
            self._get_video()
        queue: Queue[list[str]] = Queue(1)
        find_event_by_id(EventID.ANSWER_REQUESTED).invoke(
            "\n".join(tips), queue)
        return queue.get()

    def _go_to_next_question(self):
        action_row = self.last_page.locator(TestSelectors.TEST_ACTION_ROW)
        next_button = action_row.locator(
            TestSelectors.TEST_NEXT_QUESTION_BTN)
        if next_button.is_enabled():
            next_button.click(
                delay=uniform(ANSWER_SLEEP_MIN_SECS,
                              ANSWER_SLEEP_MAX_SECS)*1000
            )
        else:
            action_row.locator(TestSelectors.TEST_SUBMIT_BTN).click(
                delay=uniform(ANSWER_SLEEP_MIN_SECS,
                              ANSWER_SLEEP_MAX_SECS)*1000
            )

        if not self._handle_captcha():
            error(get_language_string("core-error-captcha-failed"))

        loading = self.last_page.locator(Selectors.LOADING)
        if loading.count() > 0:
            debug(get_language_string("core-debug-found-loading"))
            loading.wait_for(state="hidden")

        self.last_page.wait_for_load_state()

    def _do_answer(self, elements: Locator, blank: bool, tips: list[str], title: str | None = None) -> bool:

        def do_answer(answers: list[str]) -> bool:
            handled = False
            if len(answers) > 0:
                if len(answers) > elements.count():
                    warning(get_language_string(
                        "core-warning-too-much-answers"))
                debug(get_language_string(
                    "core-debug-final-answer-list") % answers)

                for i in range(len(answers)):
                    if blank:
                        if i <= elements.count():
                            debug(get_language_string(
                                "core-debug-filling-blank"))
                            self._fill_blank(elements.nth(i), answers[i])
                            handled = True
                    else:
                        for j in range(elements.count()):
                            if answers[i] in clean_string(elements.nth(j).inner_text()):
                                debug(get_language_string(
                                    "core-debug-choosing-choice") % elements.nth(j))
                                self._chose_answer(elements.nth(j))
                                handled = True
            return handled

        if title == None:
            title = tips[0]
        if do_answer(find_answer_in_answer_sources(title)):
            return True
        answer_from_page = self._get_answer_from_page()
        if do_answer(answer_from_page):
            return True
        error(get_language_string("core-error-no-answer-found"))
        tips.append(
            get_language_string("core-available-tips") +
            ANSWER_CONNECTOR.join(answer_from_page)
        )
        answers_from_manual_input = self._get_answer_from_manual_input(tips)
        if do_answer(answers_from_manual_input):
            add_answer_to_all_sources(title, answers_from_manual_input)
            return True
        warning(get_language_string("core-warning-no-valid-answer"))
        if blank:
            for i in range(elements.count()):
                self._fill_blank(elements.nth(
                    i), gen_random_string())
        else:
            self._chose_answer(elements.nth(
                randint(0, elements.count())))
        return False

    def _handle_captcha(self) -> bool:

        def handle_drag_captcha(captcha: Locator) -> bool:
            target_x = 298
            target_y = 32
            slider = captcha.locator(TestSelectors.TEST_CAPTCHA_SLIDER)
            target = captcha.locator(TestSelectors.TEST_CAPTCHA_TARGET)
            target_box = target.bounding_box()
            if target_box != None:
                target_x = round(target_box["width"])
                target_y = round(target_box["height"])
            slider.drag_to(
                target,
                target_position={
                    "x": target_x,
                    "y": target_y
                }
            )
            return captcha.is_hidden()
        captcha = self.last_page.locator(TestSelectors.TEST_CAPTCHA_SWIPER)
        if captcha.locator(TestSelectors.TEST_CAPTCHA_TEXT).count() > 0:
            warning(get_language_string("core-warning-captcha-found"))
            return any([handle_drag_captcha(captcha)])
        return True

    def _get_video(self):
        video_player = self.last_page.locator(TestSelectors.TEST_VIDEO_PLAYER)
        if video_player.count() > 0:
            # The count should always be 1...
            for i in range(video_player.count()):
                video_player.nth(i).hover()
                try:
                    with self.last_page.expect_response(VIDEO_REQUEST_REGEX) as response:
                        video_player.nth(i).locator(
                            TestSelectors.TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    error(get_language_string(
                        "core-error-test-download-video-failed"))
                else:
                    if response.value.url.endswith(".mp4"):
                        info(get_language_string(
                            "core-info-test-download-video-success"))
                        with open(get_cache_path(str(i) + "video.mp4"), "wb") as writer:
                            writer.write(response.value.body())
                    elif response.value.url.endswith(".m3u8"):
                        url = urlparse(response.value.url)
                        prefix = "%s://%s" % (
                            url.scheme,
                            url.netloc + "/".join(url.path.split("/")[:-1])
                        )
                        m3u8_path = get_cache_path(str(i) + "video.m3u8")
                        try:
                            loads(response.value.text(), prefix).dump(  # type: ignore
                                m3u8_path)
                            from ffmpeg import FFmpeg  # type: ignore
                            ffmpeg = FFmpeg().option("y")  # type: ignore
                            ffmpeg = ffmpeg.input(m3u8_path)  # type: ignore
                            ffmpeg = ffmpeg.output(  # type: ignore
                                get_cache_path(str(i) + "video.mp4"), vcodec="copy")
                            ffmpeg.execute()
                        except:
                            error(get_language_string(
                                "core-error-test-download-video-failed"))
                    else:
                        error(get_language_string(
                            "core-error-test-download-video-failed"))

    def _is_test_finished(self) -> bool:
        result = self.last_page.locator(TestSelectors.TEST_RESULT)
        if self._wait_locator(result.last, WAIT_RESULT_SECS * 1000):
            return result.count() > 0
        return False

    def _fill_blank(self, blank: Locator, text: str):
        blank.clear()
        blank.page.wait_for_timeout(
            uniform(ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)
        blank.fill(text)

    def _chose_answer(self, choice: Locator):
        if "chosen" not in (choice.get_attribute("class") or ""):
            choice.click(delay=uniform(
                ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)


class DailyTestTask(_TestTask):

    @property
    def handles(self) -> list[str]:
        return ["每日答题"]

    def __enter__(self):
        self.last_page.goto(DAILY_EXAM_PAGE)
        info(get_language_string("core-info-processing-daily-test"))
        return self


class WeeklyTestTask(_TestTask):

    @property
    def handles(self) -> list[str]:
        return ["每周答题"]

    def __enter__(self):
        self.last_page.goto(WEEKLY_EXAM_PAGE)
        self.last_page.locator(Selectors.LOADING).wait_for(state="hidden")
        weeks = self.last_page.locator(TestSelectors.TEST_WEEKS)
        weeks.last.wait_for()
        week = self._get_first_available_week(weeks)
        while week == None:
            next_btn = self.last_page.locator(TestSelectors.TEST_NEXT_PAGE)
            warning(get_language_string("core-warning-no-test-on-current-page"))
            if (next_btn.get_attribute("aria-disabled") or "") == "true":
                error(get_language_string("core-error-no-available-test"))
                self.status = TaskStatus.FAILED
                return self
            else:
                next_btn.first.click()
                self.last_page.locator(
                    Selectors.LOADING).wait_for(state="hidden")
                week = self._get_first_available_week(weeks)
        title = clean_string(week.locator(
            TestSelectors.TEST_WEEK_TITLE).inner_text())
        info(get_language_string("core-info-processing-weekly-test") % title)
        week.locator(TestSelectors.TEST_BTN).click()
        return self

    def _get_first_available_week(self, weeks: Locator) -> Locator | None:
        for i in range(weeks.count()):
            week = weeks.nth(i)
            stat = week.locator(
                TestSelectors.TEST_WEEK_STAT).get_attribute("class") or "done"
            if "done" not in stat:
                return week


class SpecialTestTask(_TestTask):

    @property
    def handles(self) -> list[str]:
        return ["专项答题"]

    def __enter__(self):
        self.last_page.goto(SPECIAL_EXAM_PAGE)
        self.last_page.locator(Selectors.LOADING).wait_for(state="hidden")
        items = self.last_page.locator(TestSelectors.TEST_ITEMS)
        items.last.wait_for()
        item = self._get_first_available_item(items)
        while item == None:
            next_btn = self.last_page.locator(TestSelectors.TEST_NEXT_PAGE)
            warning(get_language_string("core-warning-no-test-on-current-page"))
            if (next_btn.get_attribute("aria-disabled") or "") == "true":
                error(get_language_string("core-error-no-available-test"))
                self.status = TaskStatus.FAILED
                return self
            else:
                next_btn.first.click()
                self.last_page.locator(
                    Selectors.LOADING).wait_for(state="hidden")
                item = self._get_first_available_item(items)
        title_element = item.locator(TestSelectors.TEST_SPECIAL_TITLE)
        before_text = title_element.locator(
            TestSelectors.TEST_SPECIAL_TITLE_BEFORE).inner_text()
        after_text = title_element.locator(
            TestSelectors.TEST_SPECIAL_TITLE_AFTER).inner_text()
        title = clean_string(title_element.inner_text().removeprefix(
            before_text).removesuffix(after_text))
        info(get_language_string("core-info-processing-special-test") % title)
        item.locator(TestSelectors.TEST_BTN).click()
        return self

    def _get_first_available_item(self, items: Locator) -> Locator | None:
        for i in range(items.count()):
            item = items.nth(i)
            if item.locator(TestSelectors.TEST_SPECIAL_SOLUTION).count() == 0:
                return item
