import os
import time
import base64
import random
import logging
import requests
from urllib.parse import urlparse
from autoxuexiplaywright.defines import urls, core, selectors
from autoxuexiplaywright.utils import misc, lang, answerutils, storage
from playwright.sync_api import Page, TimeoutError, sync_playwright

__all__ = ["start"]
cache = set[str]()


def start(*args, **kwargs) -> None:
    run(*args, **kwargs)


def run(*args, **kwargs) -> None:
    cache.clear()
    misc.init_logger(*args, **kwargs)
    answerutils.init_sources(**kwargs)
    start_time = time.time()
    with sync_playwright() as p:
        browser = p[kwargs.get("browser", "firefox")].launch(
            headless=not kwargs.get("debug", False), proxy=kwargs.get("proxy"),
            channel=kwargs.get("channel"), args=["--mute-audio"], devtools=not kwargs.get("debug", False),
            firefox_user_prefs={"media.volume_scale": "0.0"}, executable_path=kwargs.get("executable_path", None))
        if os.path.exists(storage.get_cache_path("cookies.json")):
            context = browser.new_context(
                storage_state=storage.get_cache_path("cookies.json"))
        else:
            context = browser.new_context()
        context.set_default_timeout(core.WAIT_PAGE_SECS*1000)
        try:
            login(context.new_page(), **kwargs)
            check_status_and_finish(
                context.new_page(),  **kwargs)
        except Exception as e:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-err-process-exception") % e)
        context.close()
        browser.close()
    answerutils.close_sources()
    if not kwargs.get("debug", False):
        if os.path.exists(storage.get_cache_path("video.mp4")):
            os.remove(storage.get_cache_path("video.mp4"))
        if os.path.exists(storage.get_cache_path("qr.png")):
            os.remove(storage.get_cache_path("qr.png"))
    job_finish_signal = kwargs.get("job_finish_signal")
    if kwargs.get("gui", True) and (job_finish_signal is not None):
        job_finish_signal.emit()
    delta_mins, delta_secs = divmod(time.time()-start_time, 60)
    delta_hrs, delta_mins = divmod(delta_mins, 60)
    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get("lang", "zh-cn"),
                                                     "core-info-all-finished").format(int(delta_hrs), int(delta_mins), int(delta_secs)))


def login(page: Page, **kwargs) -> None:
    update_status_signal = kwargs.get("update_status_signal")
    if kwargs.get("gui", True) and (update_status_signal is not None):
        update_status_signal.emit(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "ui-status-loging-in"))
    page.bring_to_front()
    page.goto(urls.LOGIN_PAGE)
    try:
        page.locator(selectors.LOGIN_CHECK).wait_for(
            timeout=core.CHECK_ELEMENT_TIMEOUT_SECS*1000)
    except TimeoutError:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-failed"))
        failed_num = 0
        while True:
            qglogin = page.locator(selectors.LOGIN_QGLOGIN)
            try:
                qglogin.scroll_into_view_if_needed()
            except TimeoutError:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-err-load-qr-failed"))
                raise RuntimeError()
            locator = qglogin.frame_locator(
                selectors.LOGIN_IFRAME).locator(selectors.LOGIN_IMAGE)
            img = base64.b64decode(misc.to_str(
                locator.get_attribute("src")).split(",")[1])
            with open(storage.get_cache_path("qr.png"), "wb") as writer:
                writer.write(img)
            logging.getLogger(core.APPID).info(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-scan-required"))
            misc.img2shell(img, **kwargs)
            locator = page.locator(selectors.LOGIN_CHECK)
            try:
                locator.wait_for()
            except TimeoutError as e:
                if failed_num > core.LOGIN_RETRY_TIMES:
                    logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-err-login-failed-too-many-times"))
                    raise e
                else:
                    failed_num += 1
                    page.reload()
            else:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-qr-login-success"))
                break
    else:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-success"))
    page.close()
    qr_control_signal = kwargs.get("qr_control_signal")
    if kwargs.get("gui", True) and (qr_control_signal is not None):
        qr_control_signal.emit("".encode())
    page.context.storage_state(
        path=storage.get_cache_path("cookies.json"))


def check_status_and_finish(page: Page,  **kwargs) -> None:
    process_position = 1  # login must be finished on app
    while True:
        page.goto(urls.POINTS_PAGE)
        try:
            points = page.locator(selectors.POINTS_SPAN)
            for i in range(2):
                points.nth(i).wait_for()
            points_ints = tuple([int(point.strip())
                                for point in points.all_inner_texts()])
        except:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-update-score-failed"))
        else:
            logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-info-update-score-success") % points_ints)
            update_score_signal = kwargs.get("update_score_signal")
            if kwargs.get("gui", True) and (update_score_signal is not None):
                update_score_signal.emit(points_ints)
        cards = page.locator(selectors.POINTS_CARDS)
        cards.last.wait_for()
        login_task_style = misc.to_str(cards.nth(0).locator(
            selectors.CARD_BUTTON).first.get_attribute("style"))
        if "not-allowed" not in login_task_style:
            logging.getLogger(core.APPID).warning(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-warning-login-task-not-completed"))
        if process_position < cards.count():
            card = cards.nth(process_position)
            title = card.locator(selectors.CARD_TITLE).first.inner_text()
            button = card.locator(selectors.CARD_BUTTON).first
            style = misc.to_str(button.get_attribute("style"))
            if "not-allowed" in style:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-finished") % title)
                process_position += 1
            else:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-card-processing") % title)
                update_status_signal = kwargs.get("update_status_signal")
                if kwargs.get("gui", True) and (update_status_signal is not None):
                    update_status_signal.emit(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "ui-status-tooltip") % title)
                try:
                    with page.context.expect_page(timeout=core.WAIT_NEW_PAGE_SECS*1000) as page_event:
                        button.click()
                except TimeoutError:
                    target_page = page
                    close_page = False
                else:
                    target_page = page_event.value
                    close_page = True
                if process_position in core.NEWS_RANGE:
                    process_type = core.ProcessType.NEWS
                elif process_position in core.VIDEO_RANGE:
                    process_type = core.ProcessType.VIDEO
                elif process_position in core.TEST_RANGE:
                    process_type = core.ProcessType.TEST
                else:
                    process_type = core.ProcessType.UNKNOWN
                if pre_handle(target_page, close_page, process_type,  **kwargs):
                    process_position += 1
                page.context.storage_state(
                    path=storage.get_cache_path("cookies.json"))
        else:
            break
    page.close()


def pre_handle(page: Page, close_page: bool, process_type: core.ProcessType,  **kwargs) -> bool:
    skip = True
    if process_type == core.ProcessType.NEWS:
        with page.context.expect_page() as page_info:
            page.locator(selectors.NEWS_TITLE_SPAN).click()
        skip = handle_news(page_info.value, **kwargs)
        page_info.value.close()
    elif process_type == core.ProcessType.VIDEO:
        page.locator(selectors.VIDEO_ENTRANCE).hover()
        with page.context.expect_page() as page_info:
            page.locator(selectors.VIDEO_ENTRANCE).click()
        with page_info.value.context.expect_page() as page_info_new:
            page_info.value.locator(selectors.VIDEO_LIBRARY).click()
        skip = handle_video(page_info_new.value, **kwargs)
        page_info_new.value.close()
        page_info.value.close()
    elif process_type == core.ProcessType.TEST:
        skip = handle_test(page,  **kwargs)
    if close_page:
        page.close()
    return skip


def handle_news(page: Page, **kwargs) -> bool:
    skip = False
    news_list = page.locator(selectors.NEWS_LIST)
    news_list.last.wait_for()
    while True:
        handled_page = False
        for i in range(news_list.count()):
            title = news_list.nth(i).locator(selectors.NEWS_TITLE_TEXT)
            if title.inner_text() not in cache:
                logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-info-processing-news") % title.inner_text().strip().replace("\n", " "))
                with page.context.expect_page() as page_info:
                    title.click()
                emulate_read(page_info.value)
                cache.add(title.inner_text())
                handled_page = True
                page_info.value.close()
                break
        if not handled_page:
            next_btn = page.locator(selectors.NEXT_PAGE)
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-no-news-on-current-page"))
            if next_btn.count() == 0:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-error-no-available-news"))
                skip = True
                break
            else:
                next_btn.first.click()
                page.locator(selectors.LOADING).wait_for(state="hidden")
        else:
            break
    return skip


def handle_video(page: Page, **kwargs) -> bool:
    skip = False
    text_wrappers = page.locator(selectors.VIDEO_TEXT_WRAPPER)
    while True:
        text_wrappers.last.wait_for()
        handled_page = False
        for i in range(text_wrappers.count()):
            text_wrapper = text_wrappers.nth(i)
            if text_wrapper.inner_text() not in cache:
                logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-info-processing-video") % text_wrapper.inner_text())
                with page.context.expect_page() as page_info_video:
                    text_wrapper.click()
                emulate_read(page_info_video.value, **kwargs)
                cache.add(text_wrapper.inner_text())
                handled_page = True
                page_info_video.value.close()
                break
        if not handled_page:
            next_btn = page.locator(selectors.NEXT_PAGE)
            logging.getLogger(core.APPID).warning(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-warning-no-videos-on-current-page"))
            if next_btn.count() == 0:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-error-no-available-videos"))
                skip = True
                break
            else:
                next_btn.first.click()
                page.locator(selectors.LOADING).wait_for(state="hidden")
        else:
            break
    return skip


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


def handle_test(page: Page,  **kwargs) -> bool:
    skip = False
    if page.url == urls.DAILY_EXAM_PAGE:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-processing-daily-test"))
        emulate_answer(page, **kwargs)
    elif page.url == urls.WEEKLY_EXAM_PAGE:
        while True:
            weeks = page.locator(selectors.TEST_WEEKS)
            weeks.last.wait_for()
            handled_page = False
            for i in range(weeks.count()):
                week = weeks.nth(i)
                title = week.locator(
                    selectors.TEST_WEEK_TITLE).inner_text().strip().replace("\n", " ")
                button = week.locator(selectors.TEST_BTN)
                stat = misc.to_str(week.locator(
                    selectors.TEST_WEEK_STAT).get_attribute("class"))
                if "done" not in stat:
                    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-info-processing-weekly-test") % title)
                    button.click()
                    emulate_answer(page, **kwargs)
                    handled_page = True
                    break
            if not handled_page:
                next_btn = page.locator(selectors.TEST_NEXT_PAGE)
                logging.getLogger(core.APPID).warning(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-warning-no-test-on-current-page"))
                if next_btn.get_attribute("aria-disabled") == "true":
                    logging.getLogger(core.APPID).error(lang.get_lang(
                        kwargs.get("lang", "zh-cn"), "core-error-no-available-test"))
                    skip = True
                    break
                elif next_btn.get_attribute("aria-disabled") == "false":
                    next_btn.click()
                    page.locator(selectors.LOADING).wait_for(state="hidden")
                else:
                    break
            else:
                break
    elif page.url == urls.SPECIAL_EXAM_PAGE:
        while True:
            items = page.locator(selectors.TEST_ITEMS)
            items.last.wait_for()
            handled_page = False
            for i in range(items.count()):
                item = items.nth(i)
                points = item.locator(selectors.TEST_SPECIAL_POINTS)
                button = item.locator(selectors.TEST_BTN)
                title_element = item.locator(
                    selectors.TEST_SPECIAL_TITLE)
                before = title_element.locator(
                    selectors.TEST_SPECIAL_TITLE_BEFORE).inner_text()
                after = title_element.locator(
                    selectors.TEST_SPECIAL_TITLE_AFTER).inner_text()
                title = title_element.inner_text().replace(
                    before, "").replace(after, "").strip().replace("\n", " ")
                if points.count() == 0:
                    logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-info-processing-special-test") % title)
                    button.click()
                    emulate_answer(page,  **kwargs)
                    handled_page = True
                    break
            if not handled_page:
                next_btn = page.locator(selectors.TEST_NEXT_PAGE)
                logging.getLogger(core.APPID).warning(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-warning-no-test-on-current-page"))
                if next_btn.get_attribute("aria-disabled") == "true":
                    logging.getLogger(core.APPID).error(lang.get_lang(
                        kwargs.get("lang", "zh-cn"), "core-error-no-available-test"))
                    skip = True
                    break
                elif next_btn.get_attribute("aria-disabled") == "false":
                    next_btn.click()
                    page.locator(selectors.LOADING).wait_for(state="hidden")
                else:
                    break
            else:
                break
    else:
        logging.getLogger(core.APPID).error(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-error-unknown-test"))
        skip = True
    return skip


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


class SyncQuestionItem():
    __all__ = ["do_answer"]

    def __init__(self, page: Page, **kwargs) -> None:
        self.page = page
        question = self.page.locator(selectors.QUESTION)
        self.title = question.locator(
            selectors.QUESTION_TITLE).inner_text().strip().replace("\n", " ")
        logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-info-current-question-title") % self.title)
        self.tips = self.title
        answers = question.locator(selectors.ANSWERS)
        if answers.count() == 1:
            self.answer_items = answers.locator(selectors.ANSWER_ITEM)
            self.question_type = answerutils.QuestionType.CHOICE
            self.tips += "\n"+lang.get_lang(kwargs.get("lang", "zh-cn"), "core-available-answers") + \
                core.ANSWER_CONNECTOR.join(
                    [item.strip() for item in self.answer_items.all_inner_texts()])
            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-debug-current-question-type-choice"))
        elif answers.count() == 0:
            self.answer_items = question.locator(selectors.BLANK)
            self.question_type = answerutils.QuestionType.BLANK
            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-debug-current-question-type-blank"))
        else:
            self.answer_items = None
            self.question_type = answerutils.QuestionType.UNKNOWN

    def do_answer(self, **kwargs) -> None:
        if self.answer_items is None:
            return
        manual_input = False
        answer = answerutils.get_answer_from_sources(self.title, **kwargs)
        if answer == []:
            answer = self.try_find_answer_from_page(**kwargs)
        answer = [answer_item.strip(
        ) for answer_item in answer if answerutils.is_valid_answer(answer_item.strip())]
        logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-final-answer-list") % answer)
        if answer == []:
            self.try_get_video(**kwargs)
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-no-answer-found"))
            answer = answerutils.request_answer(self.tips, **kwargs)
        if answer == []:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-no-answer-even-tried-manual-input"))
        else:
            manual_input = True
        answer_items_count = self.answer_items.count(
        ) if self.answer_items is not None else 0
        answer_count = len(answer)
        logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-answer-items-count-and-answers-count") % (answer_items_count, answer_count))
        if answer_count > 0:
            if answer_count < answer_items_count:
                # normal status
                operated = False
                while not operated:
                    answer_start_pos = 0
                    if answer_start_pos <= answer_items_count:
                        for answer_str in answer:
                            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                                "lang", "zh-cn"), "core-debug-current-answer-text") % answer_str)
                            for j in range(answer_start_pos, answer_items_count):
                                if self.question_type == answerutils.QuestionType.CHOICE:
                                    current_choice = self.answer_items.nth(j)
                                    class_str = misc.to_str(
                                        current_choice.get_attribute("class"))
                                    text_str = current_choice.inner_text().strip()
                                    logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                                        "lang", "zh-cn"), "core-debug-current-choice-class") % class_str)
                                    logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                                        "lang", "zh-cn"), "core-debug-current-choice-text") % text_str)
                                    if (answer_str in text_str) and ("chosen" not in class_str):
                                        current_choice.click(delay=random.uniform(
                                            core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                                        operated = True
                                elif self.question_type == answerutils.QuestionType.BLANK:
                                    self.answer_items.nth(j).type(answer_str, delay=random.uniform(
                                        core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                                    operated = True
                                if operated:
                                    answer_start_pos = j+1
                                    break
                        if not operated:
                            # answer on webpage is not correct, input nothing to skip
                            answer = answerutils.request_answer(
                                self.tips, **kwargs)
                            if answer == []:
                                self.random_finish(**kwargs)
                                operated = True
                            else:
                                manual_input = True
                    else:
                        # force break loop
                        operated = True
            else:
                # should choose all
                for i in range(answer_items_count):
                    if self.question_type == answerutils.QuestionType.CHOICE:
                        self.answer_items.nth(i).click(delay=random.uniform(
                            core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                    elif self.question_type == answerutils.QuestionType.BLANK:
                        self.answer_items.nth(i).type(answer[i], delay=random.uniform(
                            core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            # no answer, random finish
            self.random_finish(**kwargs)
        # submit answer or finish test
        action_row = self.page.locator(selectors.TEST_ACTION_ROW)
        next_btn = action_row.locator(selectors.TEST_NEXT_QUESTION_BTN)
        if next_btn.is_enabled():
            next_btn.click(delay=random.uniform(
                core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        else:
            action_row.locator(selectors.TEST_SUBMIT_BTN).click(delay=random.uniform(
                core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        if self.page.locator(selectors.TEST_SOLUTION).count() > 0:
            logging.getLogger(core.APPID).error(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-error-answer-is-wrong") % self.title)
            next_btn.click(delay=random.uniform(
                core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
        elif (answer != []) and manual_input:
            answerutils.add_answer(self.title, answer)

    def try_find_answer_from_page(self, **kwargs) -> list[str]:
        answer = []
        tips = self.page.locator(
            selectors.QUESTION).locator(selectors.TIPS)
        if "ant-popover-open" not in misc.to_str(tips.get_attribute("class")):
            tips.click()
        popover = self.page.locator(selectors.POPOVER)
        if "ant-popover-hidden" not in misc.to_str(popover.get_attribute("class")):
            font = popover.locator(selectors.ANSWER_FONT)
            if font.count() > 0:
                font.last.wait_for()
                answer = [text.strip() for text in font.all_inner_texts()]
                self.tips += "\n"+lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-available-tips")+core.ANSWER_CONNECTOR.join(answer)
                logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                    "lang", "zh-cn"), "core-debug-raw-answer-list") % answer)
        if "ant-popover-open" in misc.to_str(tips.get_attribute("class")):
            tips.click()
        return answer

    def try_get_video(self, **kwargs) -> None:
        video_player = self.page.locator(selectors.TEST_VIDEO_PLAYER)
        if video_player.count() > 0:
            for i in range(video_player.count()):
                video_player.nth(i).hover()
                try:
                    with self.page.expect_response(core.VIDEO_REQUEST_REGEX) as response_info:
                        video_player.nth(i).locator(
                            selectors.TEST_VIDEO_PLAY_BTN).click()
                except TimeoutError:
                    logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-error-test-download-video-failed"))
                else:
                    try:
                        if response_info.value.url.endswith(".mp4"):
                            with open(storage.get_cache_path("video.mp4"), "wb") as writer:
                                writer.write(response_info.value.body())
                        elif response_info.value.url.endswith(".m3u8"):
                            url = urlparse(response_info.value.url)
                            prefix = "%s://%s/" % (url.scheme, url.netloc +
                                                   "/".join(url.path.split("/")[:-1]))
                            for line in response_info.value.text().split("\n"):
                                if not line.startswith("#"):
                                    with open(storage.get_cache_path("video.mp4"), "ab") as writer:
                                        writer.write(requests.get(
                                            url=prefix+line, headers=response_info.value.request.all_headers()).content)
                    except:
                        logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                            "lang", "zh-cn"), "core-error-test-download-video-failed"))
                    else:
                        logging.getLogger(core.APPID).info(lang.get_lang(kwargs.get(
                            "lang", "zh-cn"), "core-info-test-download-video-success"))

    def random_finish(self, **kwargs) -> None:
        logging.getLogger(core.APPID).error(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-error-use-random-answer"))
        if self.answer_items is not None:
            for i in range(self.answer_items.count()):
                if self.question_type == answerutils.QuestionType.CHOICE:
                    self.answer_items.nth(i).click(delay=random.uniform(
                        core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
                elif self.question_type == answerutils.QuestionType.BLANK:
                    self.answer_items.nth(i).type(answerutils.gen_random_str(), delay=random.uniform(
                        core.ANSWER_SLEEP_MIN_SECS, core.ANSWER_SLEEP_MAX_SECS)*1000)
