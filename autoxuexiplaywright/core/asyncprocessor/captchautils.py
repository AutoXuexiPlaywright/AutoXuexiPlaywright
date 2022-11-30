from playwright.async_api import Locator


async def try_finish_captcha(captcha: Locator):
    count = await captcha.count()
    for i in range(count):
        locator = captcha.nth(i)


__all__ = ["try_finish_captcha"]
