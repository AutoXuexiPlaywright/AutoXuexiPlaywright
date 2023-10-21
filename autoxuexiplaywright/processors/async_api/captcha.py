from playwright.async_api import Locator
# Relative imports
from ..common.selectors import TestSelectors


async def handle_drag_captcha(captcha: Locator) -> bool:
    await captcha.page.wait_for_timeout(300000)
    return await captcha.is_hidden()