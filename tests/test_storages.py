from importlib.resources import files as resource_files, as_file as resource_as_file
from platform import system
from os import environ, removedirs, listdir
from os.path import expanduser, join, split
from autoxuexiplaywright.storage import get_cache_path, get_config_path, get_data_path, get_resources_path
from autoxuexiplaywright.defines import APPNAME


def test_get_cache_path():
    test = get_cache_path("test")
    match system():
        case "Windows":
            assert test == join(expanduser("~"), "AppData",
                                "Local", APPNAME, "test")
        case "Linux":
            xdg_cache_home = environ.get("XDG_CACHE_HOME")
            if xdg_cache_home == None:
                xdg_cache_home = join(expanduser("~"), ".cache")
            assert test == join(xdg_cache_home, APPNAME, "test")
        case "Darwin":
            assert test == join(expanduser("~"), "Library",
                                "Caches", APPNAME, "test")
        case _:
            assert test == join(expanduser("~"), ".cache", APPNAME, "test")
    parent = split(test)[0]
    if len(listdir(parent)) == 0:
        removedirs(parent)


def test_get_config_path():
    test = get_config_path("test")
    match system():
        case "Windows":
            assert test == join(expanduser("~"), "AppData",
                                "Local", APPNAME, "test")
        case "Linux":
            xdg_config_home = environ.get("XDG_CONFIG_HOME")
            if xdg_config_home == None:
                xdg_config_home = join(expanduser("~"), ".config")
            assert test == join(xdg_config_home, APPNAME, "test")
        case "Darwin":
            assert test == join(expanduser("~"), "Library",
                                "Preferences", APPNAME, "test")
        case _:
            assert test == join(expanduser("~"), ".config", APPNAME, "test")
    parent = split(test)[0]
    if len(listdir(parent)) == 0:
        removedirs(parent)


def test_get_data_path():
    test = get_data_path("test")
    match system():
        case "Windows":
            assert test == join(expanduser("~"), "AppData",
                                "Local", APPNAME, "test")
        case "Linux":
            xdg_data_home = environ.get("XDG_DATA_HOME")
            if xdg_data_home == None:
                xdg_data_home = join(expanduser("~"), ".local", "share")
            assert test == join(xdg_data_home, APPNAME, "test")
        case "Darwin":
            assert test == join(expanduser("~"), "Library",
                                "Application Support", APPNAME, "test")
        case _:
            assert test == join(expanduser("~"), ".local",
                                "share", APPNAME, "test")
    parent = split(test)[0]
    if len(listdir(parent)) == 0:
        removedirs(parent)


def test_get_resources_path():
    try:
        get_resources_path("no-such-file")
    except FileNotFoundError:
        pass
    with resource_as_file(resource_files("autoxuexiplaywright") / "resources" / "README.txt") as path:
        assert get_resources_path("README.txt") == str(path.absolute())
