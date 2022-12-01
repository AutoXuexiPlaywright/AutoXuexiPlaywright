import random
from playwright.async_api import Locator
from autoxuexiplaywright.defines import selectors


async def try_finish_captcha(captcha: Locator):
    await finish_drag_captcha(captcha)


async def finish_drag_captcha(captcha: Locator):
    target_x = 298
    target_y = 32
    slider = captcha.locator(selectors.TEST_CAPTCHA_SLIDER)
    text = captcha.locator(selectors.TEST_CAPTCHA_TEXT)
    await slider.drag_to(
        text,
        target_position={
            "x": random.randint(target_x, target_x+5),
            "y": random.randint(0, target_y)
        }
    )


__all__ = ["try_finish_captcha"]
