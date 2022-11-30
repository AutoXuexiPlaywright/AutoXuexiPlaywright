from playwright.async_api import Locator


async def try_finish_captcha(captcha: Locator):
    for i in range(await captcha.count()):
        locator = captcha.nth(i)


__all__ = ["try_finish_captcha"]
