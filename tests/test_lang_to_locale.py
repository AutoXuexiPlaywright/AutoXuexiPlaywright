"""Test if lang_to_locale works."""

from autoxuexiplaywright.gui import lang_to_locale


_maps = {
    "ar": "ar",
    "zh-cn": "zh_CN",
}


def test_lang_to_locale():
    """Check if lang_to_locale is correct."""
    for k, v in _maps.items():
        assert lang_to_locale(k) == v
