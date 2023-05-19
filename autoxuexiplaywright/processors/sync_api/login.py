from typing import Self
from base64 import b64decode
from playwright.sync_api import TimeoutError, Page, Locator
# Relative imports
from .task import Task
from ..common import CHECK_ELEMENT_TIMEOUT_SECS, RETRY_TIMES
from ..common.selectors import LoginSelectors
from ..common.urls import LOGIN_PAGE
from ...events import EventID, find_event_by_id
from ...languages import get_language_string
from ...logger import info, error
from ...storage import get_cache_path


class LoginTask(Task):

    @property
    def requires(self) -> list[str]:
        return []

    @property
    def handles(self) -> list[str]:
        return ["登录"]

    def __enter__(self) -> Self:
        self.last_page.goto(LOGIN_PAGE)
        self.last_page.bring_to_front()
        return self

    def finish(self) -> bool:
        success = False
        if self._wait_locator(self.last_page.locator(LoginSelectors.LOGIN_CHECK).first, CHECK_ELEMENT_TIMEOUT_SECS * 1000):
            info(get_language_string("core-info-cookie-login-success"))
            success = True
        else:
            info(get_language_string("core-info-cookie-login-failed"))
            # Scan QR Code
            failed_login = 0
            while (not success) and (failed_login <= RETRY_TIMES):
                qglogin = self.last_page.locator(LoginSelectors.LOGIN_QGLOGIN)
                try:
                    qglogin.first.wait_for()
                    qglogin.first.scroll_into_view_if_needed()
                except TimeoutError as e:
                    failed_login, raise_exception = self._on_timeout(
                        failed_login, get_language_string("core-err-load-qr-failed"))
                    if raise_exception:
                        raise e
                else:
                    image = qglogin.first.frame_locator(
                        LoginSelectors.LOGIN_IFRAME).locator(LoginSelectors.LOGIN_IMAGE)
                    image.first.wait_for()
                    image_bytes = self._get_image_bytes(image.first)
                    info(get_language_string("core-info-scan-required"))
                    find_event_by_id(EventID.QR_UPDATED).invoke(image_bytes)
                    login_check = self.last_page.locator(
                        LoginSelectors.LOGIN_CHECK)
                    try:
                        login_check.first.wait_for()
                    except TimeoutError as e:
                        failed_login, raise_exception = self._on_timeout(
                            failed_login, get_language_string("core-err-login-failed-too-many-times"))
                        if raise_exception:
                            raise e
                    else:
                        info(get_language_string("core-info-qr-login-success"))
                        find_event_by_id(
                            EventID.QR_UPDATED).invoke("".encode())
                        success = True

        return success

    def _on_timeout(self, failed_times: int, error_msg: str, page: Page | None = None) -> tuple[int, bool]:
        if page == None:
            page = self.last_page
        failed_times += 1
        if failed_times > RETRY_TIMES:
            error(error_msg)
            raise_exception = True
        else:
            page.reload()
            raise_exception = False
        return failed_times, raise_exception

    def _get_image_bytes(self, image_locator: Locator) -> bytes:
        image_src = image_locator.get_attribute("src") or ","
        image_src_type_and_data = image_src.split(",")
        if len(image_src_type_and_data) >= 2:
            image_src_type = image_src_type_and_data[0]
            image_src_data = image_src_type_and_data[1]
            if image_src_type.endswith("base64"):
                image_src_bytes = b64decode(image_src_data)
                with open(get_cache_path("qr.png"), "wb") as writer:
                    writer.write(image_src_bytes)
                return image_src_bytes
        raise RuntimeError("Not a valid image locator")
