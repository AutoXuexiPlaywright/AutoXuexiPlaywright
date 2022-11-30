import time
import random
import logging
from autoxuexiplaywright.defines import core, selectors
from autoxuexiplaywright.utils import misc, lang
from autoxuexiplaywright.core.syncprocessor.defines import SyncQuestionItem
from playwright.sync_api import Page


def emulate_read(page: Page, **kwargs) -> None:
    read_all_paragraphs = True
    scroll_video_subtitle = True
    start_time = time.time()
    while True:
        if (time.time()-start_time) >= core.READ_TIME_SECS:
            break
        page.wait_for_timeout(random.uniform(
            core.PROCESS_SLEEP_MIN, core.PROCESS_SLEEP_MAX)*1000)
        try:
            player = page.locator(selectors.VIDEO_PLAYER)
            if player.count() > 0:
                player.last.wait_for(timeout=core.READ_TIME_SECS*1000)
                play_btn = player.locator(selectors.PLAY_BTN)
                if "playing" not in misc.to_str(play_btn.get_attribute("class")):
                    play_btn.click(timeout=core.READ_TIME_SECS*1000)
        except:
            pass
        try:
            video_subtitle = page.locator(selectors.VIDEO_SUBTITLE)
            if video_subtitle.count() > 0 and scroll_video_subtitle:
                video_subtitle.first.scroll_into_view_if_needed()
                scroll_video_subtitle = False
            ps = page.locator(selectors.PAGE_PARAGRAPHS)
            if ps.count() > 0:
                if read_all_paragraphs:
                    for i in range(ps.count()):
                        page.wait_for_timeout(random.uniform(
                            core.PROCESS_SLEEP_MIN, core.PROCESS_SLEEP_MAX)*1000)
                        ps.nth(i).scroll_into_view_if_needed(
                            timeout=core.READ_TIME_SECS*1000)
                    read_all_paragraphs = False
                ps.nth(random.randint(0, ps.count()-1)
                       ).scroll_into_view_if_needed(timeout=core.READ_TIME_SECS*1000)
        except:
            pass


def emulate_answer(page: Page,  **kwargs) -> None:
    while True:
        SyncQuestionItem(page, **kwargs).do_answer(**kwargs)
        result = page.locator(selectors.TEST_RESULT)
        try:
            result.wait_for(timeout=core.WAIT_RESULT_SECS*1000)
        except TimeoutError:
            logging.getLogger(core.APPID).info(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-test-not-finish"))
        else:
            break
