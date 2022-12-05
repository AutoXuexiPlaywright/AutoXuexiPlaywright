from base64 import b64decode
from logging import getLogger
from playwright.async_api import Page, TimeoutError

from autoxuexiplaywright.utils.eventmanager import find_event_by_id
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.misc import to_str, img2shell
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.defines.core import (
    CHECK_ELEMENT_TIMEOUT_SECS, APPID, LOGIN_RETRY_TIMES
)
from autoxuexiplaywright.defines.urls import LOGIN_PAGE
from autoxuexiplaywright.defines.selectors import (
    LOGIN_CHECK, LOGIN_QGLOGIN, LOGIN_IFRAME, LOGIN_IMAGE
)
from autoxuexiplaywright.defines.events import EventId


async def login(page: Page, **kwargs) -> None:
    find_event_by_id(EventId.STATUS_UPDATED).invoke(get_lang(
        kwargs.get("lang", "zh-cn"), "ui-status-loging-in"))
    await page.bring_to_front()
    await page.goto(LOGIN_PAGE)
    try:
        await page.locator(LOGIN_CHECK).wait_for(
            timeout=CHECK_ELEMENT_TIMEOUT_SECS*1000)
    except TimeoutError:
        getLogger(APPID).info(get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-failed"))
        failed_num = 0
        while True:
            qglogin = page.locator(LOGIN_QGLOGIN)
            try:
                await qglogin.scroll_into_view_if_needed()
            except TimeoutError:
                getLogger(APPID).error(get_lang(
                    kwargs.get("lang", "zh-cn"), "core-err-load-qr-failed"))
                raise RuntimeError()
            locator = qglogin.frame_locator(
                LOGIN_IFRAME).locator(LOGIN_IMAGE)
            img = b64decode(to_str(
                await locator.get_attribute("src")).split(",")[1])
            with open(get_cache_path("qr.png"), "wb") as writer:
                writer.write(img)
            getLogger(APPID).info(get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-scan-required"))
            img2shell(img, **kwargs)
            locator = page.locator(LOGIN_CHECK)
            try:
                await locator.wait_for()
            except TimeoutError as e:
                if failed_num > LOGIN_RETRY_TIMES:
                    getLogger(APPID).error(get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-err-login-failed-too-many-times"))
                    raise e
                else:
                    failed_num += 1
                    await page.reload()
            else:
                getLogger(APPID).info(get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-qr-login-success"))
                break
    else:
        getLogger(APPID).info(get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-success"))
    await page.close()
    find_event_by_id(
        EventId.QR_UPDATED).invoke("".encode())
    await page.context.storage_state(
        path=get_cache_path("cookies.json"))

__all__ = ["login"]
