from random import randint
from playwright.sync_api import Locator

from autoxuexiplaywright.defines.selectors import AnswerSelectors


def try_finish_captcha(captcha: Locator):
    finish_drag_captcha(captcha)


def finish_drag_captcha(captcha: Locator):
    target_x = 298
    target_y = 32
    slider = captcha.locator(AnswerSelectors.TEST_CAPTCHA_SLIDER)
    target = captcha.locator(AnswerSelectors.TEST_CAPTCHA_TARGET)
    target_box = target.bounding_box()
    if target_box is not None:
        target_x = round(target_box["width"])
        target_y = round(target_box["height"])
    slider.drag_to(
        target,
        target_position={
            "x": randint(target_x, target_x+5),
            "y": randint(0, target_y)
        }
    )


__all__ = ["try_finish_captcha"]
