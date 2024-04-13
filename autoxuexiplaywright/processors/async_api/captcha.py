"""Functions for handling captcha."""

# Relative imports
from playwright.async_api import Locator


async def handle_drag_captcha(captcha: Locator) -> bool:
    """Handle drag captcha.

    Args:
        captcha(Locator): The captcha locator
    """
    await captcha.page.wait_for_timeout(300000)
    return await captcha.is_hidden()
