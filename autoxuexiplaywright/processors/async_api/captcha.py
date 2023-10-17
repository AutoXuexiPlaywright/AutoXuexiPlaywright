from playwright.async_api import Locator
# Relative imports
from ..common.selectors import TestSelectors


async def handle_drag_captcha(captcha: Locator) -> bool:
    target_x = 298
    target_y = 32
    slider = captcha.locator(TestSelectors.TEST_CAPTCHA_SLIDER)
    target = captcha.locator(TestSelectors.TEST_CAPTCHA_TARGET)
    target_box = await target.bounding_box()
    if target_box != None:
        target_x = round(target_box["width"])
        target_y = round(target_box["height"])
    await slider.drag_to(
        target,
        target_position={
            "x": target_x,
            "y": target_y
        }
    )
    return await captcha.is_hidden()