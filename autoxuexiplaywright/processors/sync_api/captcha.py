from playwright.sync_api import Locator
# Relative imports
from ..common.selectors import TestSelectors


def handle_drag_captcha(captcha: Locator) -> bool:
    captcha.page.wait_for_timeout(300000)
    return captcha.is_hidden()