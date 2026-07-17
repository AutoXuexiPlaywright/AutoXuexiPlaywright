"""Basic operations to emulate testing."""

from abc import ABCMeta as _ABCMeta
from random import uniform as _random_uniform
from typing import final as _final
from logging import getLogger as _get_logger
from collections.abc import Iterator as _Iterator
from collections.abc import AsyncIterator as _AsyncIterator
from playwright.async_api import Page as _Page
from playwright.async_api import Locator as _Locator
from playwright.async_api import TimeoutError as _TimeoutError
from playwright.async_api import expect as _expect
from autoxuexiplaywright.sdk import Task as _Task
from autoxuexiplaywright.sdk import AnswerSource as _AnswerSource
from autoxuexiplaywright.sdk import CaptchaHandler as _CaptchaHandler
from autoxuexiplaywright.sdk import (
    RecordSupportedAnswerSource as _RecordSupportedAnswerSource,
)
from autoxuexiplaywright.module import iter_module_type as _iter_modules
from autoxuexiplaywright.localize import gettext as __
from autoxuexiplaywright.processor.tasks.utils import clean_string as _clean_string


_logger = _get_logger(__name__)


class TestTask(_Task, metaclass=_ABCMeta):
    """Basic operations to emulate testing."""

    _DETAIL_BODY = "div.detail-body"
    _QUESTION = "div.question"
    _ACTION_ROW = "div.action-row"
    _TIPS = "div.line-feed"
    _RED_FONTS = 'font[color="red"]'
    _TIPS_BUTTON = "span.tips"
    _CHOICES = "div.q-answer.choosable"
    _QUESTION_TITLE = "div.q-body"
    _BLANKS = "input.blank"
    _RESULT = "div.practice-result"
    _SOLUTION = "div.solution"
    _NEXT_BUTTON = "button.next-btn"
    _SUBMIT_BUTTON = "button.submit-btn"
    _PAGER = "div.pager"
    _CURRENT_POSITION = "span.big"
    _CAPTCHA = (
        "div#swiper_valid, div#JS_aliyun-captcha-dialog, div#JS_aliyun-captcha-main"
    )
    _CONTROL_WAIT_TIMEOUT_MS = 10000
    _ACTION_WAIT_TIMEOUT_MS = 10000
    _CAPTCHA_WAIT_TIMEOUT_MS = 3000
    _CAPTCHA_PROBE_TIMEOUT_MS = 800
    _TRANSITION_WAIT_TIMEOUT_MS = 10000
    _STATE_POLL_INTERVAL_MS = 100
    _DO_ANSWER_SLEEP_MIN_SECS = 10
    _DO_ANSWER_SLEEP_MAX_SECS = 15

    @_final
    async def _test(self, page: _Page) -> bool:
        result = page.locator(self._RESULT)
        while await result.is_hidden():
            detail_body = page.locator(self._DETAIL_BODY)
            await detail_body.wait_for()
            question = detail_body.locator(self._QUESTION)
            await _expect(question).to_be_visible()

            question_title = question.locator(self._QUESTION_TITLE)
            await _expect(question_title).to_be_visible()
            title = _clean_string(await question_title.inner_text())
            _logger.info(
                __("Question is: %(title)s"),
                {"title": title},
            )
            choices = question.locator(self._CHOICES)
            blanks = question.locator(self._BLANKS)
            controls = question.locator(f"{self._CHOICES}, {self._BLANKS}")
            try:
                await controls.first.wait_for(timeout=self._CONTROL_WAIT_TIMEOUT_MS)
            except _TimeoutError:
                _logger.error(__("Cannot find available answer controls."))
                return False

            tips_button = question.locator(self._TIPS_BUTTON)
            tips = page.locator(self._TIPS).last
            position = 0
            choices_count = await choices.count()
            blanks_count = await blanks.count()
            choice_titles: list[str] = []
            if choices_count > 0:
                choice_titles = [
                    _clean_string(c) for c in await choices.all_inner_texts()
                ]
            if len(choice_titles) > 0:
                _logger.info(
                    __("Available choices: %(choices)s"),
                    {"choices": choice_titles},
                )
            async for answer in self.__get_answer(
                title,
                choice_titles,
                tips_button,
                tips,
            ):
                if choices_count > 0 and not await self.__choice_item(choices, answer):
                    _logger.warning(
                        __("Failed to choice the item with answer %(answer)s"),
                        {"answer": answer},
                    )

                if blanks_count > 0 and not await self.__fill_blank(
                    blanks,
                    position,
                    answer,
                ):
                    _logger.warning(
                        __(
                            "Failed to fill the blank at %(position)d with answer %(answer)s",  # noqa: E501
                        ),
                        {"position": position, "answer": answer},
                    )
                    position += 1

            action_row = detail_body.locator(self._ACTION_ROW)
            solution = detail_body.locator(self._SOLUTION)
            pager = page.locator(self._PAGER)
            total = int((await pager.inner_text()).split("/")[-1])
            current_position = pager.locator(self._CURRENT_POSITION)
            current = int(await current_position.inner_text())
            if not await self.__go_to_next_question_or_submit(
                title,
                choice_titles,
                action_row,
                solution,
            ):
                return False

            if current < total:
                _logger.debug(__("Still needs handling, continuing..."))
                await _expect(current_position).to_have_text(str(current + 1))
            else:
                _logger.info(__("Handle test completed."))
                await _expect(result).to_be_visible()

        return True

    @_final
    async def __fill_blank(self, blanks: _Locator, position: int, answer: str) -> bool:
        await blanks.last.wait_for()
        if position < await blanks.count():
            _logger.debug(
                __("Checking blank at %(position)d..."),
                {"position": position},
            )
            blank = blanks.nth(position)
            if await blank.input_value() == "" and await blank.is_editable():
                _logger.debug(
                    __("Filling blank with answer %(answer)s..."),
                    {"answer": answer},
                )
                await blank.page.wait_for_timeout(self.__sleep_seconds * 1000)
                await blank.fill(answer)
                return True
        return False

    @_final
    async def __choice_item(self, choices: _Locator, answer: str) -> bool:
        await choices.last.wait_for()
        for position in range(await choices.count()):
            _logger.debug(
                __("Checking item at %(position)d..."),
                {"position": position},
            )
            choice = choices.nth(position)
            class_of_choice = await choice.get_attribute("class") or ""
            if answer in await choice.inner_text() and "chosen" not in class_of_choice:
                _logger.debug(__("Choicing answer %(answer)s..."), {"answer": answer})
                await choice.click(delay=self.__sleep_seconds * 1000)
                return True
        return False

    @_final
    async def __get_answer(
        self,
        title: str,
        choice_titles: list[str],
        tips_button: _Locator,
        tips: _Locator,
    ) -> _AsyncIterator[str]:
        itered = False
        for source in _iter_modules(_AnswerSource):
            try:
                iterator = source.get_answer(title)
            except Exception as e:
                _logger.error(__("Failed to get answer because %(e)s"), {"e": e})
            else:
                async for answer in iterator:
                    yield answer
                    itered = True
                if itered:
                    return

        if not itered:
            _logger.debug(
                __(
                    "No answer can be found from source, trying to get from page tips...",  # noqa: E501
                ),
            )
            class_of_tips_button = await tips_button.get_attribute("class") or ""
            tips_texts: list[str] = []
            if "ant-popover-open" not in class_of_tips_button:
                await tips_button.click()
                await tips.wait_for()
            red_fonts = tips.locator(self._RED_FONTS)
            if await red_fonts.count() > 0:
                await red_fonts.last.wait_for()
                for text in await red_fonts.all_inner_texts():
                    _logger.debug(__("Found tip %(tip)s."), {"tip": text})
                    tips_texts.append(_clean_string(text))
            class_of_tips_button = await tips_button.get_attribute("class") or ""
            if "ant-popover-open" in class_of_tips_button:
                await tips_button.click()
                await tips.wait_for(state="hidden")

            for text in self.__strip_answers(title, tips_texts, choice_titles):
                yield text

    @_final
    async def __go_to_next_question_or_submit(
        self,
        title: str,
        choice_titles: list[str],
        action_row: _Locator,
        solution: _Locator,
    ) -> bool:
        button = await self.__wait_for_action_button(action_row)
        if button is None:
            _logger.error(__("Cannot found available next button or submit button."))
            return False
        is_submit = await button.get_attribute("class") or ""
        button_text = _clean_string(await button.inner_text())
        await button.click(delay=self.__sleep_seconds * 1000)

        captcha_timeout_ms = (
            self._CAPTCHA_WAIT_TIMEOUT_MS
            if "submit-btn" in is_submit or "完成" in button_text
            else self._CAPTCHA_PROBE_TIMEOUT_MS
        )
        captcha = await self.__find_visible_captcha(
            action_row.page,
            captcha_timeout_ms,
        )
        if captcha is not None and not await self.__handle_captcha(captcha):
            _logger.error(__("Failed to handle captcha"))
            return False

        if await self.__wait_for_solution_or_transition(title, solution):
            _logger.error(__("The answer to the question is wrong."))
            red_fonts = solution.locator(self._RED_FONTS)
            if await red_fonts.count() > 0:
                await red_fonts.last.wait_for()
                answers = [_clean_string(i) for i in await red_fonts.all_inner_texts()]
                await self.__update_answer(title, answers, choice_titles)
            next_button = await self.__wait_for_action_button(action_row)
            if next_button is None:
                _logger.error(__("Cannot found available next button."))
                return False
            await next_button.click(delay=self.__sleep_seconds * 1000)
        return True

    @_final
    async def __wait_for_action_button(self, action_row: _Locator) -> _Locator | None:
        elapsed_ms = 0
        while elapsed_ms < self._ACTION_WAIT_TIMEOUT_MS:
            for selector in (self._NEXT_BUTTON, self._SUBMIT_BUTTON):
                button = action_row.locator(selector).first
                if await button.count() > 0 and await button.is_enabled():
                    return button
            await action_row.page.wait_for_timeout(self._STATE_POLL_INTERVAL_MS)
            elapsed_ms += self._STATE_POLL_INTERVAL_MS
        return None

    @_final
    async def __find_visible_captcha(
        self,
        page: _Page,
        timeout_ms: int,
    ) -> _Locator | None:
        captcha = page.locator(self._CAPTCHA)
        elapsed_ms = 0
        while elapsed_ms < timeout_ms:
            for position in range(await captcha.count()):
                candidate = captcha.nth(position)
                if await candidate.is_visible():
                    return candidate
            await page.wait_for_timeout(self._STATE_POLL_INTERVAL_MS)
            elapsed_ms += self._STATE_POLL_INTERVAL_MS
        return None

    @_final
    async def __wait_for_solution_or_transition(
        self,
        title: str,
        solution: _Locator,
    ) -> bool:
        page = solution.page
        question_title = page.locator(self._QUESTION_TITLE).first
        result = page.locator(self._RESULT).first
        elapsed_ms = 0
        while elapsed_ms < self._TRANSITION_WAIT_TIMEOUT_MS:
            if await solution.count() > 0 and await solution.first.is_visible():
                return True
            if await result.is_visible():
                return False
            if await question_title.count() > 0 and await question_title.is_visible():
                current_title = _clean_string(await question_title.inner_text())
                if current_title != title:
                    return False
            await page.wait_for_timeout(self._STATE_POLL_INTERVAL_MS)
            elapsed_ms += self._STATE_POLL_INTERVAL_MS
        return False

    @_final
    async def __handle_captcha(self, captcha: _Locator) -> bool:
        for handler in _iter_modules(_CaptchaHandler):
            try:
                if await handler.solve(captcha):
                    return True
            except Exception as e:
                _logger.error(
                    __("Failed to handle captcha because %(e)s"),
                    {"e": e},
                )
        return False

    @_final
    async def __update_answer(
        self,
        title: str,
        answers: list[str],
        choice_titles: list[str],
    ):
        answers_to_record = list(self.__strip_answers(title, answers, choice_titles))

        for source in _iter_modules(_RecordSupportedAnswerSource):
            try:
                await source.record(title, answers_to_record)
            except Exception as e:
                _logger.error(__("Failed to record answer because %(e)s"), {"e": e})

    @_final
    def __strip_answers(
        self,
        title: str,
        answers: list[str],
        choice_titles: list[str],
    ) -> _Iterator[str]:
        judgement_size_match = len(answers) == 1 and len(choice_titles) == 2  # noqa: PLR2004
        judgement_content_match = all(
            any(content in title for title in choice_titles)
            for content in ["正确", "错误"]
        )
        if judgement_size_match and judgement_content_match:
            result = "正确" if answers[0] in title else "错误"
            _logger.warning(
                __("Rewriting judgement question result to %(result)s"),
                {"result": result},
            )
            yield result
            return

        _logger.debug(__("Yielding answers directly..."))
        yield from answers

    @property
    @_final
    def __sleep_seconds(self) -> float:
        return _random_uniform(  # noqa: S311
            self._DO_ANSWER_SLEEP_MIN_SECS,
            self._DO_ANSWER_SLEEP_MAX_SECS,
        )
