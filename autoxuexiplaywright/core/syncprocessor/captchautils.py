from playwright.sync_api import Locator


def try_finish_captcha(captcha: Locator):
    for i in range(captcha.count()):
        locator = captcha.nth(i)


__all__ = ["try_finish_captcha"]
