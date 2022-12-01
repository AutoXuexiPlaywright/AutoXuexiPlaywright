import base64
import logging
from playwright.async_api import Page, TimeoutError
from autoxuexiplaywright.utils import eventmanager, lang, misc, storage
from autoxuexiplaywright.defines import core, urls, selectors, events


async def login(page: Page, **kwargs) -> None:
    eventmanager.find_event_by_id(events.EventId.STATUS_UPDATED).invoke(lang.get_lang(
        kwargs.get("lang", "zh-cn"), "ui-status-loging-in"))
    await page.bring_to_front()
    await page.goto(urls.LOGIN_PAGE)
    try:
        await page.locator(selectors.LOGIN_CHECK).wait_for(
            timeout=core.CHECK_ELEMENT_TIMEOUT_SECS*1000)
    except TimeoutError:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-failed"))
        failed_num = 0
        while True:
            qglogin = page.locator(selectors.LOGIN_QGLOGIN)
            try:
                await qglogin.scroll_into_view_if_needed()
            except TimeoutError:
                logging.getLogger(core.APPID).error(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-err-load-qr-failed"))
                raise RuntimeError()
            locator = qglogin.frame_locator(
                selectors.LOGIN_IFRAME).locator(selectors.LOGIN_IMAGE)
            img = base64.b64decode(misc.to_str(
                await locator.get_attribute("src")).split(",")[1])
            with open(storage.get_cache_path("qr.png"), "wb") as writer:
                writer.write(img)
            logging.getLogger(core.APPID).info(lang.get_lang(
                kwargs.get("lang", "zh-cn"), "core-info-scan-required"))
            misc.img2shell(img, **kwargs)
            locator = page.locator(selectors.LOGIN_CHECK)
            try:
                await locator.wait_for()
            except TimeoutError as e:
                if failed_num > core.LOGIN_RETRY_TIMES:
                    logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
                        "lang", "zh-cn"), "core-err-login-failed-too-many-times"))
                    raise e
                else:
                    failed_num += 1
                    await page.reload()
            else:
                logging.getLogger(core.APPID).info(lang.get_lang(
                    kwargs.get("lang", "zh-cn"), "core-info-qr-login-success"))
                break
    else:
        logging.getLogger(core.APPID).info(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-info-cookie-login-success"))
    await page.close()
    eventmanager.find_event_by_id(
        events.EventId.QR_UPDATED).invoke("".encode())
    await page.context.storage_state(
        path=storage.get_cache_path("cookies.json"))

__all__ = ["login"]
