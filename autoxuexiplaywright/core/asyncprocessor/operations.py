import time
import random
import logging
from playwright.async_api import Page, TimeoutError
from autoxuexiplaywright.defines import core, selectors
from autoxuexiplaywright.utils import misc, lang
from autoxuexiplaywright.core.asyncprocessor.defines import AsyncQuestionItem


async def emulate_read(page: Page, **kwargs) -> None:
    read_all_paragraphs = True
    scroll_video_subtitle = True
    start_time = time.time()
    while True:
        if (time.time()-start_time) >= core.READ_TIME_SECS:
            break
        await page.wait_for_timeout(random.uniform(
            core.PROCESS_SLEEP_MIN, core.PROCESS_SLEEP_MAX)*1000)
        try:
            player = page.locator(selectors.VIDEO_PLAYER)
            if await player.count() > 0:
                await player.last.wait_for(timeout=core.READ_TIME_SECS*1000)
                play_btn = player.locator(selectors.PLAY_BTN)
                if "playing" not in misc.to_str(await play_btn.get_attribute("class")):
                    await play_btn.click(timeout=core.READ_TIME_SECS*1000)
        except:
            pass
        try:
            video_subtitle = page.locator(selectors.VIDEO_SUBTITLE)
            if await video_subtitle.count() > 0 and scroll_video_subtitle:
                await video_subtitle.first.scroll_into_view_if_needed()
                scroll_video_subtitle = False
            ps = page.locator(selectors.PAGE_PARAGRAPHS)
            if await ps.count() > 0:
                if read_all_paragraphs:
                    for i in range(await ps.count()):
                        await page.wait_for_timeout(random.uniform(
                            core.PROCESS_SLEEP_MIN, core.PROCESS_SLEEP_MAX)*1000)
                        await ps.nth(i).scroll_into_view_if_needed(
                            timeout=core.READ_TIME_SECS*1000)
                    read_all_paragraphs = False
                await ps.nth(random.randint(0, await ps.count()-1)
                             ).scroll_into_view_if_needed(timeout=core.READ_TIME_SECS*1000)
        except:
            pass


async def emulate_answer(page: Page,  **kwargs) -> None:
    while True:
        await AsyncQuestionItem(page, **kwargs).do_answer(**kwargs)
        result = page.locator(selectors.TEST_RESULT)
        try:
            await result.wait_for(timeout=core.WAIT_RESULT_SECS*1000)
        except TimeoutError:
            logging.getLogger(core.APPID).info(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-test-not-finish"))
        else:
            break
