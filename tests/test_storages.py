"""Test if storage functions are working."""

import pytest
from os import environ
from os import removedirs
from pathlib import Path
from platform import system
from importlib.resources import files as resource_files
from importlib.resources import as_file as resource_as_file
from autoxuexiplaywright.defines import APPNAME
from autoxuexiplaywright.storage import get_data_path
from autoxuexiplaywright.storage import get_cache_path
from autoxuexiplaywright.storage import get_config_path
from autoxuexiplaywright.storage import get_resources_path


@pytest.fixture()
def cache_path() -> Path:
    """Generate cache path."""
    match system():
        case "Windows":
            return Path.home() / "AppData" / "Local" / APPNAME
        case "Linux":
            xdg_cache_home = environ.get("XDG_CACHE_HOME")
            xdg_cache_home = Path(xdg_cache_home) if xdg_cache_home else Path.home() / ".cache"
            return xdg_cache_home / APPNAME
        case "Darwin":
            return Path.home() / "Library" / "Caches" / APPNAME
        case _:
            return Path.home() / ".cache" / APPNAME


@pytest.fixture()
def config_path() -> Path:
    """Generate config path."""
    match system():
        case "Windows":
            return Path.home() / "AppData" / "Local" / APPNAME
        case "Linux":
            xdg_config_home = environ.get("XDG_CONFIG_HOME")
            xdg_config_home = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
            return xdg_config_home / APPNAME
        case "Darwin":
            return Path.home() / "Library" / "Preferences" / APPNAME
        case _:
            return Path.home() / ".config" / APPNAME


@pytest.fixture()
def data_path() -> Path:
    """Generate data path."""
    match system():
        case "Windows":
            return Path.home() / "AppData" / "Local" / APPNAME
        case "Linux":
            xdg_data_home = environ.get("XDG_DATA_HOME")
            xdg_data_home = (
                Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
            )
            return xdg_data_home / APPNAME
        case "Darwin":
            return Path.home() / "Library" / "Application Support" / APPNAME
        case _:
            return Path.home() / ".local" / "share" / APPNAME


def test_get_cache_path(cache_path: Path):
    """Check if get_cache_path is correct."""
    assert get_cache_path("") == cache_path
    if len(list(cache_path.iterdir())) == 0:
        removedirs(cache_path)


def test_get_config_path(config_path: Path):
    """Check if get_config_path is correct."""
    assert get_config_path("") == config_path
    if len(list(config_path.iterdir())) == 0:
        removedirs(config_path)


def test_get_data_path(data_path: Path):
    """Check if get_data_path is correct."""
    assert get_data_path("") == data_path
    if len(list(data_path.iterdir())) == 0:
        removedirs(data_path)


def test_get_resources_path():
    """Check if get_resources_path is correct."""
    with pytest.raises(FileNotFoundError):
        _ = get_resources_path("no-such-file")
    with resource_as_file(
        resource_files("autoxuexiplaywright") / "resources" / "README.txt",
    ) as path:
        assert get_resources_path("README.txt") == path.absolute()
