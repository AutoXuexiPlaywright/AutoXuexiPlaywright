from time import time
from random import randint, uniform
from logging import getLogger
from playwright.async_api import Page, TimeoutError

from autoxuexiplaywright.defines.core import (
    READ_TIME_SECS, PROCESS_SLEEP_MIN, PROCESS_SLEEP_MAX, WAIT_RESULT_SECS, APPID)
from autoxuexiplaywright.defines.selectors import (
    VIDEO_PLAYER, PLAY_BTN, VIDEO_SUBTITLE, PAGE_PARAGRAPHS, TEST_RESULT
)
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.asyncprocessor.defines import AsyncQuestionItem


async def emulate_read(page: Page) -> None:
    read_all_paragraphs = True
    scroll_video_subtitle = True
    start_time = time()
    while True:
        if (time()-start_time) >= READ_TIME_SECS:
            break
        await page.wait_for_timeout(uniform(
            PROCESS_SLEEP_MIN, PROCESS_SLEEP_MAX)*1000)
        try:
            player = page.locator(VIDEO_PLAYER)
            if await player.count() > 0:
                await player.last.wait_for(timeout=READ_TIME_SECS*1000)
                play_btn = player.locator(PLAY_BTN)
                if "playing" not in to_str(await play_btn.get_attribute("class")):
                    await play_btn.click(timeout=READ_TIME_SECS*1000)
        except:
            pass
        try:
            video_subtitle = page.locator(VIDEO_SUBTITLE)
            if await video_subtitle.count() > 0 and scroll_video_subtitle:
                await video_subtitle.first.scroll_into_view_if_needed()
                scroll_video_subtitle = False
            ps = page.locator(PAGE_PARAGRAPHS)
            if await ps.count() > 0:
                if read_all_paragraphs:
                    for i in range(await ps.count()):
                        await page.wait_for_timeout(uniform(
                            PROCESS_SLEEP_MIN, PROCESS_SLEEP_MAX)*1000)
                        await ps.nth(i).scroll_into_view_if_needed(
                            timeout=READ_TIME_SECS*1000)
                    read_all_paragraphs = False
                await ps.nth(randint(0, await ps.count()-1)
                             ).scroll_into_view_if_needed(timeout=READ_TIME_SECS*1000)
        except:
            pass


async def emulate_answer(page: Page) -> None:
    while True:
        async with AsyncQuestionItem(page) as qi:
            await qi.do_answer()
        result = page.locator(TEST_RESULT)
        try:
            await result.wait_for(timeout=WAIT_RESULT_SECS*1000)
        except TimeoutError:
            getLogger(APPID).info(get_lang(
                Config.get_instance().lang, "core-info-test-not-finish"))
        else:
            break
