"""Handle drag captcha."""

from semver import Version as _Version
from typing import final as _final
from typing import override as _override
from logging import getLogger as _get_logger
from autoxuexiplaywright import APPAUTHOR as _APPAUTHOR
from autoxuexiplaywright import __version__ as _version
from playwright.async_api import Locator as _Locator
from playwright.async_api import TimeoutError as _TimeoutError
from autoxuexiplaywright.sdk import CaptchaHandler as _CaptchaHandler
from autoxuexiplaywright.sdk import module_entrance as _module
from autoxuexiplaywright.processor.captcha_handlers.utils import (
    build_drag_positions as _build_drag_positions,
)
from autoxuexiplaywright.processor.captcha_handlers.utils import (
    calculate_slider_max_distance as _calculate_slider_max_distance,
)


_logger = _get_logger(__name__)


@_module(_Version.parse(_version))
@_final
class DragCaptchaHandler(_CaptchaHandler):
    """Handle drag captcha."""

    _SLIDER = (
        "#aliyunCaptcha-sliding-slider, .aliyunCaptcha-sliding-slider, "
        "span.btn_slide, .btn_slide, [class*='slider-handle'], "
        "[class*='slide-btn'], [class*='slide_button']"
    )
    _TRACK = (
        "#aliyunCaptcha-sliding-body, .aliyunCaptcha-sliding-body, "
        "div.scale_text, .scale_text, [class*='slider-track'], "
        "[class*='slide-track'], [class*='scale']"
    )
    _RETRY_TIMES = 3
    _FAST_MOVE_STEPS = 45

    @property
    @_override
    def name(self) -> str:
        return self.__class__.__name__

    @property
    @_override
    def author(self) -> str:
        return _APPAUTHOR

    @_override
    async def solve(self, locator: _Locator) -> bool:
        if not await locator.is_visible():
            return False

        slider = locator.locator(self._SLIDER).first
        track = locator.locator(self._TRACK).first
        if not await slider.is_visible() or not await track.is_visible():
            return False

        for _ in range(self._RETRY_TIMES):
            slider_box = await slider.bounding_box()
            track_box = await track.bounding_box()
            if slider_box is None or track_box is None:
                return False

            start_x = slider_box["x"] + slider_box["width"] / 2
            start_y = slider_box["y"] + slider_box["height"] / 2
            distance = _calculate_slider_max_distance(slider_box, track_box)
            if distance <= 0:
                return False

            mouse = locator.page.mouse
            await mouse.move(start_x, start_y)
            await locator.page.wait_for_timeout(180)
            await mouse.down()
            await locator.page.wait_for_timeout(220)
            positions = _build_drag_positions(start_x, start_y, distance)
            for index, (x, y) in enumerate(positions):
                await mouse.move(x, y)
                await locator.page.wait_for_timeout(
                    14 if index < self._FAST_MOVE_STEPS else 22,
                )
            await locator.page.wait_for_timeout(570)
            await mouse.up()

            try:
                await locator.wait_for(state="hidden", timeout=4000)
            except _TimeoutError:
                _logger.debug("Drag captcha is still visible, retrying...")
            else:
                return True

        return False
