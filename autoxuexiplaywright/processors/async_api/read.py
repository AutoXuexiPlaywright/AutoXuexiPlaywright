from time import time
from random import randint, uniform
from playwright.async_api import Locator, TimeoutError
# Relative imports
from .task import Task, TaskStatus
from ..common import READ_TIME_SECS, READ_SLEEPS_MIN_SECS, READ_SLEEPS_MAX_SECS, cache, clean_string
from ..common.selectors import Selectors, ReadSelectors
from ..common.urls import MAIN_PAGE
from ...languages import get_language_string
from ...logger import info, warning, error, debug


class _ReadTask(Task):
    @property
    def requires(self) -> list[str]:
        return ["登录"]

    async def finish(self) -> bool:
        scroll_paragraphs_in_order = True
        scroll_video_subtitles_in_order = True
        start_time = time()
        while (time() - start_time) <= READ_TIME_SECS:
            await self.last_page.wait_for_timeout(
                uniform(READ_SLEEPS_MIN_SECS, READ_SLEEPS_MAX_SECS)*1000)
            try:
                player = self.last_page.locator(ReadSelectors.VIDEO_PLAYER)
                if await player.count() > 0:
                    await player.last.wait_for(timeout=READ_TIME_SECS*1000)
                    for i in range(await player.count()):
                        if await player.nth(i).locator(ReadSelectors.REPLAY_BTN).count() == 0:
                            await player.nth(i).hover()
                            play_btn = player.nth(i).locator(
                                ReadSelectors.PLAY_BTN)
                            if "playing" not in (await play_btn.get_attribute("class") or ""):
                                await play_btn.click()

                await self._scroll_elements(
                    self.last_page.locator(ReadSelectors.VIDEO_SUBTITLE),
                    scroll_video_subtitles_in_order
                )
                scroll_video_subtitles_in_order = False

                await self._scroll_elements(
                    self.last_page.locator(ReadSelectors.PAGE_PARAGRAPHS),
                    scroll_paragraphs_in_order
                )
                scroll_paragraphs_in_order = False
            except TimeoutError:
                pass
            except Exception as e:
                debug(get_language_string("core-debug-read-failed") % e)
                return False
        return True

    async def _scroll_elements(self, elements: Locator, order: bool):
        if (await elements.count() > 0):
            for i in range(await elements.count()):
                await self.last_page.wait_for_timeout(
                    timeout=uniform(READ_SLEEPS_MIN_SECS,
                                    READ_SLEEPS_MAX_SECS)*1000
                )
                if order:
                    await elements.nth(i).scroll_into_view_if_needed()
                else:
                    await elements.nth(randint(0, await elements.count()-1)
                                       ).scroll_into_view_if_needed()


class NewsTask(_ReadTask):

    @property
    def handles(self) -> list[str]:
        return ["我要选读文章"]

    async def __aenter__(self):
        await self.last_page.goto(MAIN_PAGE)
        title_span = self.last_page.locator(
            ReadSelectors.NEWS_TITLE_SPAN).first
        await title_span.wait_for()
        async with self.last_page.context.expect_page() as event:
            await title_span.click()
        self.pages.append(await event.value)
        news_list = self.last_page.locator(ReadSelectors.NEWS_LIST)
        await news_list.last.wait_for()
        news_title = await self._get_first_available_news_title(news_list)
        while news_title == None:
            next_btn = self.last_page.locator(ReadSelectors.NEXT_PAGE)
            warning(get_language_string("core-warning-no-news-on-current-page"))
            if await next_btn.count() == 0:
                # No more page(s) for news, mark task failed and end this function
                error(get_language_string("core-error-no-available-news"))
                self.status = TaskStatus.FAILED
                return self
            else:
                await next_btn.first.click()
                await self.last_page.locator(
                    Selectors.LOADING).wait_for(state="hidden")
                news_title = await self._get_first_available_news_title(news_list)
        info(get_language_string("core-info-processing-news") % clean_string(await news_title.inner_text()))
        async with self.last_page.context.expect_page() as event:
            await news_title.click()
        self.pages.append(await event.value)
        cache.add(clean_string(await news_title.inner_text()))

        return self

    async def _get_first_available_news_title(self, news_list: Locator) -> Locator | None:
        for i in range(await news_list.count()):
            news = news_list.nth(i)
            title_element = news.locator(ReadSelectors.NEWS_TITLE_TEXT)
            if clean_string(await title_element.inner_text()) not in cache:
                return title_element


class VideoTask(_ReadTask):

    @property
    def handles(self) -> list[str]:
        return ["视听学习", "视听学习时长"]

    async def __aenter__(self):
        await self.last_page.goto(MAIN_PAGE)
        async with self.last_page.context.expect_page() as event:
            await self.last_page.locator(ReadSelectors.VIDEO_ENTRANCE).first.click()
        self.pages.append(await event.value)
        async with self.last_page.context.expect_page() as event:
            await self.last_page.locator(ReadSelectors.VIDEO_LIBRARY).first.click()
        self.pages.append(await event.value)
        text_wrappers = self.last_page.locator(
            ReadSelectors.VIDEO_TEXT_WRAPPER)
        await text_wrappers.last.wait_for()
        text_wrapper = await self._get_first_available_video_title(text_wrappers)
        while text_wrapper == None:
            next_btn = self.last_page.locator(ReadSelectors.NEXT_PAGE)
            warning(get_language_string(
                "core-warning-no-videos-on-current-page"))
            if await next_btn.count() == 0:
                error(get_language_string("core-error-no-available-videos"))
                self.status = TaskStatus.FAILED
                return self
            else:
                await next_btn.first.click()
                await self.last_page.locator(
                    Selectors.LOADING).wait_for(state="hidden")
                text_wrapper = await self._get_first_available_video_title(
                    text_wrappers)
        info(get_language_string("core-info-processing-video") %
             clean_string(await text_wrapper.inner_text()))
        async with self.last_page.context.expect_page() as event:
            await text_wrapper.click()
        self.pages.append(await event.value)
        cache.add(clean_string(await text_wrapper.inner_text()))

        return self

    async def _get_first_available_video_title(self, video_list: Locator) -> Locator | None:
        for i in range(await video_list.count()):
            video = video_list.nth(i)
            if clean_string(await video.inner_text()) not in cache:
                return video
