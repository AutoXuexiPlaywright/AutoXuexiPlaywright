"""Test if get_runtime_config and set_runtime_config works."""

from autoxuexiplaywright.config import Config
from autoxuexiplaywright.config import get_runtime_config
from autoxuexiplaywright.config import set_runtime_config


_config = Config()


def test_set_runtime_config():
    """Check if set_runtime_config is correct."""
    set_runtime_config(_config)


def test_get_runtime_config():
    """Check if get_runtime_config is correct."""
    set_runtime_config(_config)
    assert get_runtime_config() == _config
