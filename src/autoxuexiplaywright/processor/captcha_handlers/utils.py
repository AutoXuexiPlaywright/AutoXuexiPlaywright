"""Utilities for drag captcha handlers."""

from random import uniform as _random_uniform
from collections.abc import Mapping as _Mapping


def calculate_slider_max_distance(
    slider_box: _Mapping[str, float],
    target_box: _Mapping[str, float],
) -> float:
    """Return the distance that aligns the slider with the track right edge."""
    return max(
        0.0,
        float(target_box["x"])
        + float(target_box["width"])
        - float(slider_box["x"])
        - float(slider_box["width"]),
    )


def build_drag_positions(
    start_x: float,
    start_y: float,
    distance: float,
    steps: int = 58,
) -> list[tuple[float, float]]:
    """Build a smooth drag path whose final position is exact."""
    distance = max(0.0, float(distance))
    steps = max(8, int(steps))
    positions: list[tuple[float, float]] = []
    for index in range(1, steps + 1):
        progress = index / steps
        eased = 3.0 * progress * progress - 2.0 * progress * progress * progress
        x = start_x + distance * eased
        y = (
            start_y if index == steps else start_y + _random_uniform(-1.25, 1.25)  # noqa: S311
        )
        positions.append((x, y))
    positions[-1] = (start_x + distance, start_y)
    return positions
