from time import time
from random import uniform, randint
from logging import getLogger
from playwright.sync_api import Page, TimeoutError

from autoxuexiplaywright.defines.core import (
    READ_TIME_SECS, PROCESS_SLEEP_MIN, PROCESS_SLEEP_MAX, WAIT_RESULT_SECS
)
from autoxuexiplaywright.defines.selectors import ReadSelectors, AnswerSelectors
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.syncprocessor.defines import SyncQuestionItem

from autoxuexiplaywright import appid


def emulate_read(page: Page) -> None:
    read_all_paragraphs = True
    scroll_video_subtitle = True
    start_time = time()
    while True:
        if (time()-start_time) >= READ_TIME_SECS:
            break
        page.wait_for_timeout(uniform(
            PROCESS_SLEEP_MIN, PROCESS_SLEEP_MAX)*1000)
        try:
            player = page.locator(ReadSelectors.VIDEO_PLAYER)
            if player.count() > 0:
                player.last.wait_for(timeout=READ_TIME_SECS*1000)
                play_btn = player.locator(ReadSelectors.PLAY_BTN)
                if "playing" not in to_str(play_btn.get_attribute("class")):
                    play_btn.click(timeout=READ_TIME_SECS*1000)
        except:
            pass
        try:
            video_subtitle = page.locator(ReadSelectors.VIDEO_SUBTITLE)
            if video_subtitle.count() > 0 and scroll_video_subtitle:
                video_subtitle.first.scroll_into_view_if_needed()
                scroll_video_subtitle = False
            ps = page.locator(ReadSelectors.PAGE_PARAGRAPHS)
            if ps.count() > 0:
                if read_all_paragraphs:
                    for i in range(ps.count()):
                        page.wait_for_timeout(uniform(
                            PROCESS_SLEEP_MIN, PROCESS_SLEEP_MAX)*1000)
                        ps.nth(i).scroll_into_view_if_needed(
                            timeout=READ_TIME_SECS*1000)
                    read_all_paragraphs = False
                ps.nth(randint(0, ps.count()-1)
                       ).scroll_into_view_if_needed(timeout=READ_TIME_SECS*1000)
        except:
            pass


def emulate_answer(page: Page) -> None:
    while True:
        with SyncQuestionItem(page) as qi:
            qi.do_answer()
        result = page.locator(AnswerSelectors.TEST_RESULT)
        try:
            result.wait_for(timeout=WAIT_RESULT_SECS*1000)
        except TimeoutError:
            getLogger(appid).info(get_lang(
                Config.get_instance().lang, "core-info-test-not-finish"))
        else:
            break
