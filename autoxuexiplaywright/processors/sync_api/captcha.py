"""Functions for handling captcha."""

# Relative imports
from playwright.sync_api import Locator


def handle_drag_captcha(captcha: Locator) -> bool:
    """Handle drag captcha.

    Args:
        captcha(Locator): The captcha locator
    """
    captcha.page.wait_for_timeout(300000)
    return captcha.is_hidden()
