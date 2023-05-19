from random import randint, uniform
from queue import Queue
from urllib.parse import urlparse
from playwright.async_api import Locator, TimeoutError
# Relative imports
from .task import Task, TaskStatus
from ..common import WAIT_RESULT_SECS, WAIT_CHOICE_SECS, ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS, VIDEO_REQUEST_REGEX, ANSWER_CONNECTOR, clean_string
from ..common.answer.utils import is_valid_answer, gen_random_string
from ..common.answer.sources import add_answer_to_all_sources, find_answer_in_answer_sources
from ..common.selectors import Selectors, TestSelectors
from ..common.urls import DAILY_EXAM_PAGE, WEEKLY_EXAM_PAGE, SPECIAL_EXAM_PAGE
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

    async def finish(self) -> bool:
        while not await self._is_test_finished():
            # Get question title and choice(s) or title only
            question = self.last_page.locator(TestSelectors.QUESTION).last
            await question.scroll_into_view_if_needed()
            choices = question.locator(TestSelectors.ANSWERS)
            await self._wait_locator(choices.last, WAIT_CHOICE_SECS * 1000)
            title_element = question.locator(TestSelectors.QUESTION_TITLE).last
            await title_element.scroll_into_view_if_needed()
            title = clean_string(await title_element.inner_text())
            info(get_language_string("core-info-current-question-title") % title)
            tips = [title]
            match await choices.count():
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
                        [clean_string(item) for item in await items_to_answer.all_inner_texts()])
                    )
                    debug(get_language_string(
                        "core-debug-current-question-type-choice"))
                case _:
                    self.status = TaskStatus.FAILED
                    return False
            if not await self._do_answer(items_to_answer, await choices.count() == 0, tips):
                error(get_language_string("core-error-answer-failed"))
            await self._go_to_next_question()
            if await self.last_page.locator(TestSelectors.TEST_SOLUTION).count() > 0:
                error(get_language_string("core-error-answer-is-wrong") % title)
                await self._go_to_next_question()
        return True

    async def _get_answer_from_page(self) -> list[str]:
        answer_on_page: list[str] = []
        tips = self.last_page.locator(
            TestSelectors.QUESTION).locator(TestSelectors.TIPS)
        if "ant-popover-open" not in (await tips.get_attribute("class") or ""):
            await tips.click()
        popover = self.last_page.locator(TestSelectors.POPOVER)
        if "ant-popover-hidden" not in (await popover.get_attribute("class") or ""):
            font = popover.locator(TestSelectors.ANSWER_FONT)
            await self._wait_locator(font.last)
            if await font.count() > 0:
                answer_on_page_raw = [clean_string(text)
                                      for text in await font.all_inner_texts()]
                for answer in answer_on_page_raw:
                    if is_valid_answer(answer):
                        answer_on_page.append(answer)
        if "ant-popover-open" in (await tips.get_attribute("class") or ""):
            await tips.click()
        debug(get_language_string("core-debug-raw-answer-list") % answer_on_page)
        return answer_on_page

    async def _get_answer_from_manual_input(self, tips: list[str]) -> list[str]:
        if _config.get_video:
            await self._get_video()
        queue: Queue[list[str]] = Queue(1)
        find_event_by_id(EventID.ANSWER_REQUESTED).invoke(
            "\n".join(tips), queue)
        return queue.get()

    async def _go_to_next_question(self):
        action_row = self.last_page.locator(TestSelectors.TEST_ACTION_ROW)
        next_button = action_row.locator(
            TestSelectors.TEST_NEXT_QUESTION_BTN)
        if await next_button.is_enabled():
            await next_button.click(
                delay=uniform(ANSWER_SLEEP_MIN_SECS,
                              ANSWER_SLEEP_MAX_SECS)*1000
            )

        else:
            await action_row.locator(TestSelectors.TEST_SUBMIT_BTN).click(
                delay=uniform(ANSWER_SLEEP_MIN_SECS,
                              ANSWER_SLEEP_MAX_SECS)*1000
            )
        if not await self._handle_captcha():
            error(get_language_string("core-error-captcha-failed"))

        loading = self.last_page.locator(Selectors.LOADING)
        if await loading.count() > 0:
            debug(get_language_string("core-debug-found-loading"))
            await loading.wait_for(state="hidden")

        await self.last_page.wait_for_load_state()

    async def _do_answer(self, elements: Locator, blank: bool, tips: list[str], title: str | None = None) -> bool:

        async def do_answer(answers: list[str]) -> bool:
            handled = False
            if len(answers) > 0:
                if len(answers) > await elements.count():
                    warning(get_language_string(
                        "core-warning-too-much-answers"))
                debug(get_language_string(
                    "core-debug-final-answer-list") % answers)

                for i in range(len(answers)):
                    if blank:
                        if i <= await elements.count():
                            debug(get_language_string(
                                "core-debug-filling-blank"))
                            await self._fill_blank(elements.nth(i), answers[i])
                            handled = True
                    else:
                        for j in range(await elements.count()):
                            if answers[i] in clean_string(await elements.nth(j).inner_text()):
                                debug(get_language_string(
                                    "core-debug-choosing-choice") % elements.nth(j))
                                await self._chose_answer(elements.nth(j))
                                handled = True
            return handled

        if title == None:
            title = tips[0]
        if await do_answer(find_answer_in_answer_sources(title)):
            return True
        answer_from_page = await self._get_answer_from_page()
        if await do_answer(answer_from_page):
            return True
        error(get_language_string("core-error-no-answer-found"))
        tips.append(
            get_language_string("core-available-tips") +
            ANSWER_CONNECTOR.join(answer_from_page)
        )
        answers_from_manual_input = await self._get_answer_from_manual_input(tips)
        if await do_answer(answers_from_manual_input):
            add_answer_to_all_sources(title, answers_from_manual_input)
            return True
        warning(get_language_string("core-warning-no-valid-answer"))
        if blank:
            for i in range(await elements.count()):
                await self._fill_blank(elements.nth(
                    i), gen_random_string())
        else:
            await self._chose_answer(elements.nth(
                randint(0, await elements.count())))
        return False

    async def _handle_captcha(self) -> bool:

        async def handle_drag_captcha(captcha: Locator) -> bool:
            target_x = 298
            target_y = 32
            slider = captcha.locator(TestSelectors.TEST_CAPTCHA_SLIDER)
            target = captcha.locator(TestSelectors.TEST_CAPTCHA_TARGET)
            target_box = await target.bounding_box()
            if target_box != None:
                target_x = round(target_box["width"])
                target_y = round(target_box["height"])
            await slider.drag_to(
                target,
                target_position={
                    "x": target_x,
                    "y": target_y
                }
            )
            return await captcha.is_hidden()
        captcha = self.last_page.locator(TestSelectors.TEST_CAPTCHA_SWIPER)
        if await captcha.locator(TestSelectors.TEST_CAPTCHA_TEXT).count() > 0:
            warning(get_language_string("core-warning-captcha-found"))
            return any([await handle_drag_captcha(captcha)])
        return True

    async def _get_video(self):
        video_player = self.last_page.locator(TestSelectors.TEST_VIDEO_PLAYER)
        if await video_player.count() > 0:
            # The count should always be 1...
            for i in range(await video_player.count()):
                await video_player.nth(i).hover()
                try:
                    async with self.last_page.expect_response(VIDEO_REQUEST_REGEX) as response:
                        await video_player.nth(i).locator(
                            TestSelectors.TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    error(get_language_string(
                        "core-error-test-download-video-failed"))
                else:
                    if (await response.value).url.endswith(".mp4"):
                        info(get_language_string(
                            "core-info-test-download-video-success"))
                        with open(get_cache_path(str(i) + "video.mp4"), "wb") as writer:
                            writer.write(await (await response.value).body())
                    elif (await response.value).url.endswith(".m3u8"):
                        url = urlparse((await response.value).url)
                        prefix = "%s://%s" % (
                            url.scheme,
                            url.netloc + "/".join(url.path.split("/")[:-1])
                        )
                        m3u8_path = get_cache_path(str(i) + "video.m3u8")
                        try:
                            loads(response.value.text(), prefix).dump(  # type: ignore
                                m3u8_path)
                            from ffmpeg.asyncio import FFmpeg  # type: ignore
                            ffmpeg = FFmpeg().option("y")  # type: ignore
                            ffmpeg = ffmpeg.input(m3u8_path)  # type: ignore
                            ffmpeg = ffmpeg.output(  # type: ignore
                                get_cache_path(str(i) + "video.mp4"), vcodec="copy")
                            await ffmpeg.execute()
                        except:
                            error(get_language_string(
                                "core-error-test-download-video-failed"))
                    else:
                        error(get_language_string(
                            "core-error-test-download-video-failed"))

    async def _is_test_finished(self) -> bool:
        result = self.last_page.locator(TestSelectors.TEST_RESULT)
        if await self._wait_locator(result.last, WAIT_RESULT_SECS * 1000):
            return await result.count() > 0
        return False

    async def _fill_blank(self, blank: Locator, text: str):
        await blank.clear()
        await blank.type(text, delay=uniform(ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)

    async def _chose_answer(self, choice: Locator):
        if "chosen" not in (await choice.get_attribute("class") or ""):
            await choice.click(delay=uniform(ANSWER_SLEEP_MIN_SECS, ANSWER_SLEEP_MAX_SECS)*1000)


class DailyTestTask(_TestTask):

    @property
    def handles(self) -> list[str]:
        return ["每日答题"]

    async def __aenter__(self):
        await self.last_page.goto(DAILY_EXAM_PAGE)
        info(get_language_string("core-info-processing-daily-test"))
        return self


class WeeklyTestTask(_TestTask):

    @property
    def handles(self) -> list[str]:
        return ["每周答题"]

    async def __aenter__(self):
        await self.last_page.goto(WEEKLY_EXAM_PAGE)
        await self.last_page.locator(Selectors.LOADING).wait_for(state="hidden")
        weeks = self.last_page.locator(TestSelectors.TEST_WEEKS)
        await weeks.last.wait_for()
        week = await self._get_first_available_week(weeks)
        while week == None:
            next_btn = self.last_page.locator(TestSelectors.TEST_NEXT_PAGE)
            warning(get_language_string("core-warning-no-test-on-current-page"))
            if (await next_btn.get_attribute("aria-disabled") or "") == "true":
                error(get_language_string("core-error-no-available-test"))
                self.status = TaskStatus.FAILED
                return self
            else:
                await next_btn.first.click()
                await self.last_page.locator(
                    Selectors.LOADING).wait_for(state="hidden")
                week = await self._get_first_available_week(weeks)
        title = clean_string(await week.locator(
            TestSelectors.TEST_WEEK_TITLE).inner_text())
        info(get_language_string("core-info-processing-weekly-test") % title)
        await week.locator(TestSelectors.TEST_BTN).click()
        return self

    async def _get_first_available_week(self, weeks: Locator) -> Locator | None:
        for i in range(await weeks.count()):
            week = weeks.nth(i)
            stat = await (week.locator(
                TestSelectors.TEST_WEEK_STAT).get_attribute("class")) or "done"
            if "done" not in stat:
                return week


class SpecialTestTask(_TestTask):

    @property
    def handles(self) -> list[str]:
        return ["专项答题"]

    async def __aenter__(self):
        await self.last_page.goto(SPECIAL_EXAM_PAGE)
        await self.last_page.locator(Selectors.LOADING).wait_for(state="hidden")
        items = self.last_page.locator(TestSelectors.TEST_ITEMS)
        await items.last.wait_for()
        item = await self._get_first_available_item(items)
        while item == None:
            next_btn = self.last_page.locator(TestSelectors.TEST_NEXT_PAGE)
            warning(get_language_string("core-warning-no-test-on-current-page"))
            if (await next_btn.get_attribute("aria-disabled") or "") == "true":
                error(get_language_string("core-error-no-available-test"))
                self.status = TaskStatus.FAILED
                return self
            else:
                await next_btn.first.click()
                await self.last_page.locator(
                    Selectors.LOADING).wait_for(state="hidden")
                item = await self._get_first_available_item(items)
        title_element = item.locator(TestSelectors.TEST_SPECIAL_TITLE)
        before_text = await title_element.locator(
            TestSelectors.TEST_SPECIAL_TITLE_BEFORE).inner_text()
        after_text = await title_element.locator(
            TestSelectors.TEST_SPECIAL_TITLE_AFTER).inner_text()
        title = clean_string((await title_element.inner_text()).removeprefix(
            before_text).removesuffix(after_text))
        info(get_language_string("core-info-processing-special-test") % title)
        await item.locator(TestSelectors.TEST_BTN).click()
        return self

    async def _get_first_available_item(self, items: Locator) -> Locator | None:
        for i in range(await items.count()):
            item = items.nth(i)
            if await item.locator(TestSelectors.TEST_SPECIAL_SOLUTION).count() == 0:
                return item
