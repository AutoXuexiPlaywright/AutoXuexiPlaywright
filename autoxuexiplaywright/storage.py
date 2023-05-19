from os import listdir, makedirs, environ
from os.path import join, exists, isdir, expanduser, basename
from platform import system
from importlib.resources import files as resource_files, as_file as resource_as_file
# Relative imports
from .defines import APPNAME

_LINUX_SHARED_BASE = "/usr/share/autoxuexiplaywright"

_path: dict[str, str | None] = {
    "resources_user": None,
    "resources_system": None,
    "cache": None,
    "config": None,
    "data": None,
    "modules_user": None,
    "modules_system": None
}

_modules: list[str] = []


def get_cache_path(name: str) -> str:
    """Get full path of a cache file/folder

    **Note**: The file/folder may not be exist

    Args:
        name (str): The file/folder name to get

    Returns:
        str: The full path
    """
    if not isinstance(_path["cache"], str):
        _path["cache"] = _get_cache_home()
    return join(_path["cache"], name)


def get_config_path(name: str) -> str:
    """Get full path of a config file/folder

    **Note**: The file/dir may not be exist

    Args:
        name (str): The file/dir name to get

    Returns:
        str: The full path
    """
    if not isinstance(_path["config"], str):
        _path["config"] = _get_config_home()
    return join(_path["config"], name)


def get_data_path(name: str) -> str:
    """Get full path of a data file/dir

    **Note**: The file/dir may not be exist

    Args:
        name (str): The file/dir name to get

    Returns:
        str: The full path
    """
    if not isinstance(_path["data"], str):
        _path["data"] = _get_data_home()
    return join(_path["data"], name)


def get_modules_file_paths(mod_ext: str) -> list[str]:
    """Get all modules files

    Args:
        mod_ext (str): The extension of module

    Returns:
        list[str]: The modules
    """
    user_modules_file_names: list[str] = []
    if len(_modules) == 0:
        # Find all user modules
        if not isinstance(_path["modules_user"], str):
            _path["modules_user"] = join(get_data_path("modules"))
        if isdir(_path["modules_user"]):
            for file in listdir(_path["modules_user"]):
                if file.endswith(mod_ext):
                    user_modules_file_names.append(basename(file))
                    _modules.append(file)
        if system() == "Linux":
            # Linux has a shared modules path
            if not isinstance(_path["modules_system"], str):
                _path["modules_system"] = join(_LINUX_SHARED_BASE, "modules")
            if isdir(_path["modules_system"]):
                for file in listdir(_path["modules_system"]):
                    if file.endswith(mod_ext):
                        if basename(file) not in user_modules_file_names:
                            _modules.append(file)
    return _modules


def get_resources_path(file_name: str) -> str:
    """Get full path of a resource file

    Args:
        file_name (str): The filename to get

    Raises:
        FileNotFoundError: When no such file

    Returns:
        str: The full path
    """
    if not isinstance(_path["resources_user"], str):
        _path["resources_user"] = get_data_path("resources")
    user_override = join(_path["resources_user"], file_name)
    if exists(user_override):
        return user_override

    if system() == "Linux":
        # Linux has a system wide path to make package manager happy
        if not isinstance(_path["resources_system"], str):
            _path["resources_system"] = join(_LINUX_SHARED_BASE, "resources")
        system_wide = join(_path["resources_system"], file_name)
        if exists(system_wide):
            return system_wide

    # Those files are in the /resources folder
    with resource_as_file(resource_files("autoxuexiplaywright") / "resources" / file_name) as path:
        if exists(path):
            return str(path.absolute())

    raise FileNotFoundError("No such file: "+file_name)


def _get_data_home() -> str:
    """Get data storage path

    Returns:
        str: The full path to store data
    """
    match system():
        case "Windows":
            path = join(expanduser("~"), "AppData", "Local", APPNAME)
            makedirs(path, exist_ok=True)
            return path
        case "Linux":
            xdg_data_home = environ.get("XDG_DATA_HOME")
            if xdg_data_home == None:
                xdg_data_home = join(expanduser("~"), ".local", "share")
            app_data = join(xdg_data_home, APPNAME)
            makedirs(app_data, exist_ok=True)
            return app_data
        case "Darwin":
            path = join(expanduser("~"), "Library",
                        "Application Support", APPNAME)
            makedirs(path, exist_ok=True)
            return path
        case _:
            path = join(expanduser("~"), ".local", "share", APPNAME)
            makedirs(path, exist_ok=True)
            return path


def _get_config_home() -> str:
    """Get config storage path

    Returns:
        str: The full path to store config
    """
    match system():
        case "Windows":
            path = join(expanduser("~"), "AppData", "Local", APPNAME)
            makedirs(path, exist_ok=True)
            return path
        case "Linux":
            xdg_config_home = environ.get("XDG_CONFIG_HOME")
            if xdg_config_home == None:
                xdg_config_home = join(expanduser("~"), ".config")
            app_config = join(xdg_config_home, APPNAME)
            makedirs(app_config, exist_ok=True)
            return app_config
        case "Darwin":
            path = join(expanduser("~"), "Library", "Preferences", APPNAME)
            makedirs(path, exist_ok=True)
            return path
        case _:
            path = join(expanduser("~"), ".config", APPNAME)
            makedirs(path, exist_ok=True)
            return path


def _get_cache_home() -> str:
    """Get cache storage path

    Returns:
        str: The full path to store config
    """
    match system():
        case "Windows":
            path = join(expanduser("~"), "AppData", "Local", APPNAME)
            makedirs(path, exist_ok=True)
            return path
        case "Linux":
            xdg_cache_home = environ.get("XDG_CACHE_HOME")
            if xdg_cache_home == None:
                xdg_cache_home = join(expanduser("~"), ".cache")
            app_cache = join(xdg_cache_home, APPNAME)
            makedirs(app_cache, exist_ok=True)
            return app_cache
        case "Darwin":
            path = join(expanduser("~"), "Library", "Caches", APPNAME)
            makedirs(path, exist_ok=True)
            return path
        case _:
            path = join(expanduser("~"), ".cache", APPNAME)
            makedirs(path, exist_ok=True)
            return path
