from random import randint
from playwright.async_api import Locator

from autoxuexiplaywright.defines.selectors import AnswerSelectors


async def try_finish_captcha(captcha: Locator):
    await finish_drag_captcha(captcha)


async def finish_drag_captcha(captcha: Locator):
    target_x = 298
    target_y = 32
    slider = captcha.locator(AnswerSelectors.TEST_CAPTCHA_SLIDER)
    target = captcha.locator(AnswerSelectors.TEST_CAPTCHA_TARGET)
    target_box = await target.bounding_box()
    if target_box is not None:
        target_x = round(target_box["width"])
        target_y = round(target_box["height"])
    await slider.drag_to(
        target,
        target_position={
            "x": randint(target_x, target_x+5),
            "y": randint(0, target_y)
        }
    )


__all__ = ["try_finish_captcha"]
