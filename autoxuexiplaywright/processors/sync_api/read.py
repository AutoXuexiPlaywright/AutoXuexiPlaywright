"""Classes and functions for handling read task."""

from time import time

# Relative imports
from .task import Task
from .task import TaskStatus
from random import randint
from random import uniform
from typing import Self
from ..common import READ_TIME_SECS
from ..common import READ_SLEEPS_MAX_SECS
from ..common import READ_SLEEPS_MIN_SECS
from ..common import cache
from ..common import clean_string
from ...logger import info
from ...logger import debug
from ...logger import error
from ...logger import warning
from ...languages import get_language_string
from ..common.urls import MAIN_PAGE
from typing_extensions import override
from ..common.selectors import Selectors
from ..common.selectors import ReadSelectors
from playwright.sync_api import Locator
from playwright.sync_api import TimeoutError


class _ReadTask(Task):
    @property
    @override
    def requires(self) -> list[str]:
        return ["登录"]

    @override
    def finish(self) -> bool:
        scroll_paragraphs_in_order = True
        scroll_video_subtitles_in_order = True
        start_time = time()
        while (time() - start_time) <= READ_TIME_SECS:
            self.last_page.wait_for_timeout(
                uniform(READ_SLEEPS_MIN_SECS, READ_SLEEPS_MAX_SECS) * 1000,
            )
            try:
                player = self.last_page.locator(ReadSelectors.VIDEO_PLAYER)
                if player.count() > 0:
                    player.last.wait_for(timeout=READ_TIME_SECS * 1000)
                    for i in range(player.count()):
                        if player.nth(i).locator(ReadSelectors.REPLAY_BTN).count() == 0:
                            player.nth(i).hover()
                            play_btn = player.nth(i).locator(ReadSelectors.PLAY_BTN)
                            if "playing" not in (play_btn.get_attribute("class") or ""):
                                play_btn.click()

                self._scroll_elements(
                    self.last_page.locator(ReadSelectors.VIDEO_SUBTITLE),
                    scroll_video_subtitles_in_order,
                )
                scroll_video_subtitles_in_order = False

                self._scroll_elements(
                    self.last_page.locator(ReadSelectors.PAGE_PARAGRAPHS),
                    scroll_paragraphs_in_order,
                )
                scroll_paragraphs_in_order = False
            except TimeoutError:
                pass
            except Exception as e:
                debug(get_language_string("core-debug-read-failed") % e)
                return False
        return True

    def _scroll_elements(self, elements: Locator, order: bool):
        if elements.count() > 0:
            for i in range(elements.count()):
                self.last_page.wait_for_timeout(
                    timeout=uniform(READ_SLEEPS_MIN_SECS, READ_SLEEPS_MAX_SECS) * 1000,
                )
                if order:
                    elements.nth(i).scroll_into_view_if_needed()
                else:
                    elements.nth(
                        randint(0, elements.count() - 1),
                    ).scroll_into_view_if_needed()


class NewsTask(_ReadTask):
    """Task for handling news."""
    @property
    @override
    def handles(self) -> list[str]:
        return ["我要选读文章"]

    @override
    def __enter__(self) -> Self:
        self.last_page.goto(MAIN_PAGE)
        title_span = self.last_page.locator(ReadSelectors.NEWS_TITLE_SPAN).first
        title_span.wait_for()
        with self.last_page.context.expect_page() as event:
            title_span.click()
        self.pages.append(event.value)
        news_list = self.last_page.locator(ReadSelectors.NEWS_LIST)
        news_list.last.wait_for()
        news_title = self._get_first_available_news_title(news_list)
        while not news_title:
            next_btn = self.last_page.locator(ReadSelectors.NEXT_PAGE)
            warning(get_language_string("core-warning-no-news-on-current-page"))
            if next_btn.count() == 0:
                # No more page(s) for news, mark task failed and end this function
                error(get_language_string("core-error-no-available-news"))
                self.status = TaskStatus.FAILED
                return self
            next_btn.first.click()
            self.last_page.locator(Selectors.LOADING).wait_for(state="hidden")
            news_title = self._get_first_available_news_title(news_list)
        info(
            get_language_string("core-info-processing-news")
            % clean_string(news_title.inner_text()),
        )
        with self.last_page.context.expect_page() as event:
            news_title.click()
        self.pages.append(event.value)
        cache.add(clean_string(news_title.inner_text()))

        return self

    def _get_first_available_news_title(self, news_list: Locator) -> Locator | None:
        for i in range(news_list.count()):
            news = news_list.nth(i)
            title_element = news.locator(ReadSelectors.NEWS_TITLE_TEXT)
            if clean_string(title_element.inner_text()) not in cache:
                return title_element
        return None


class VideoTask(_ReadTask):
    """Task for handling video."""
    @property
    @override
    def handles(self) -> list[str]:
        return ["视听学习", "视听学习时长", "我要视听学习"]

    @override
    def __enter__(self) -> Self:
        self.last_page.goto(MAIN_PAGE)
        with self.last_page.context.expect_page() as event:
            self.last_page.locator(ReadSelectors.VIDEO_ENTRANCE).first.click()
        self.pages.append(event.value)
        with self.last_page.context.expect_page() as event:
            self.last_page.locator(ReadSelectors.VIDEO_LIBRARY).first.click()
        self.pages.append(event.value)
        text_wrappers = self.last_page.locator(ReadSelectors.VIDEO_TEXT_WRAPPER)
        text_wrappers.last.wait_for()
        text_wrapper = self._get_first_available_video_title(text_wrappers)
        while not text_wrapper:
            next_btn = self.last_page.locator(ReadSelectors.NEXT_PAGE)
            warning(get_language_string("core-warning-no-videos-on-current-page"))
            if next_btn.count() == 0:
                error(get_language_string("core-error-no-available-videos"))
                self.status = TaskStatus.FAILED
                return self
            next_btn.first.click()
            self.last_page.locator(Selectors.LOADING).wait_for(state="hidden")
            text_wrapper = self._get_first_available_video_title(text_wrappers)
        info(
            get_language_string("core-info-processing-video")
            % clean_string(text_wrapper.inner_text()),
        )
        with self.last_page.context.expect_page() as event:
            text_wrapper.click()
        self.pages.append(event.value)
        cache.add(clean_string(text_wrapper.inner_text()))

        return self

    def _get_first_available_video_title(self, video_list: Locator) -> Locator | None:
        for i in range(video_list.count()):
            video = video_list.nth(i)
            if clean_string(video.inner_text()) not in cache:
                return video
        return None
