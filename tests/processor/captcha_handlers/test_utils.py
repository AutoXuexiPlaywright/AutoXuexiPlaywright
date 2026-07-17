"""Test drag captcha utilities."""

import pytest
from autoxuexiplaywright.processor.captcha_handlers.utils import (
    build_drag_positions as _build_drag_positions,
)
from autoxuexiplaywright.processor.captcha_handlers.utils import (
    calculate_slider_max_distance as _calculate_slider_max_distance,
)


def test_calculate_slider_max_distance() -> None:
    """The slider should stop with its right edge at the track right edge."""
    expected_distance = 320.0
    slider = {"x": 100.0, "y": 20.0, "width": 40.0, "height": 40.0}
    target = {"x": 100.0, "y": 20.0, "width": 360.0, "height": 40.0}

    assert _calculate_slider_max_distance(slider, target) == expected_distance  # noqa: S101


def test_calculate_slider_max_distance_clamps_negative_distance() -> None:
    """An invalid target geometry should not result in a backwards drag."""
    slider = {"x": 100.0, "y": 20.0, "width": 40.0, "height": 40.0}
    target = {"x": 80.0, "y": 20.0, "width": 20.0, "height": 40.0}

    assert _calculate_slider_max_distance(slider, target) == 0.0  # noqa: S101


def test_build_drag_positions_ends_exactly_at_target() -> None:
    """A generated drag path should be monotonic and end exactly at target."""
    minimum_steps = 8
    positions = _build_drag_positions(100.0, 40.0, 320.0, steps=4)
    x_positions = [position[0] for position in positions]

    assert len(positions) == minimum_steps  # noqa: S101
    assert positions[-1] == (420.0, 40.0)  # noqa: S101
    assert x_positions == sorted(x_positions)  # noqa: S101


def test_build_drag_positions_clamps_negative_distance() -> None:
    """A negative distance should keep the final pointer at its start."""
    positions = _build_drag_positions(100.0, 40.0, -20.0)

    assert positions[-1] == pytest.approx((100.0, 40.0))  # noqa: S101
