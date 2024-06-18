"""Test if get_language_string is correct."""

import pytest
from json import load
from autoxuexiplaywright.config import Config
from autoxuexiplaywright.config import set_runtime_config
from autoxuexiplaywright.storage import get_resources_path
from autoxuexiplaywright.languages import NoSuchLanguageKeyException
from autoxuexiplaywright.languages import get_language_string


def test_language_string():
    """Check if get_language_string works."""
    set_runtime_config(Config())  # lang="zh-cn"
    with (get_resources_path("lang") / "zh-cn.json").open("r", encoding="utf-8") as reader:
        language_json: dict[str, str] = load(reader)
    for key, value in language_json.items():
        assert get_language_string(key) == value
    with pytest.raises(NoSuchLanguageKeyException):
        _ = get_language_string("_test-key-not-exist")
