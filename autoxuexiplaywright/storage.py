"""Classes and functions for storaging."""

from os import environ
from pathlib import Path

# Relative imports
from .defines import APPNAME
from platform import system
from importlib.resources import files as resource_files
from importlib.resources import as_file as resource_as_file


_LINUX_SHARED_BASE = Path("/usr/share/autoxuexiplaywright")

_path: dict[str, Path | None] = {
    "resources_user": None,
    "resources_system": None,
    "cache": None,
    "config": None,
    "data": None,
    "modules_user": None,
    "modules_system": None,
}

_modules: list[Path] = []


def get_cache_path(name: str) -> Path:
    """Get full path of a cache file/folder.

    **Note**: The file/folder may not be exist

    Args:
        name (str): The file/folder name to get

    Returns:
        Path: The full path
    """
    if not _path["cache"]:
        _path["cache"] = _get_cache_home()
    return _path["cache"] / name


def get_config_path(name: str) -> Path:
    """Get full path of a config file/folder.

    **Note**: The file/dir may not be exist

    Args:
        name (str): The file/dir name to get

    Returns:
        Path: The full path
    """
    if not _path["config"]:
        _path["config"] = _get_config_home()
    return _path["config"] / name


def get_data_path(name: str) -> Path:
    """Get full path of a data file/dir.

    **Note**: The file/dir may not be exist

    Args:
        name (str): The file/dir name to get

    Returns:
        Path: The full path
    """
    if not _path["data"]:
        _path["data"] = _get_data_home()
    return _path["data"] / name


def get_modules_file_paths(mod_ext: str) -> list[Path]:
    """Get all modules files.

    Args:
        mod_ext (str): The extension of module

    Returns:
        list[Path]: The modules
    """
    user_modules_file_names: list[str] = []
    if len(_modules) == 0:
        # Find all user modules
        if not _path["modules_user"]:
            _path["modules_user"] = get_data_path("modules")
        if _path["modules_user"].is_dir():
            for file in _path["modules_user"].iterdir():
                if file.name.endswith(mod_ext):
                    user_modules_file_names.append(file.name)
                    _modules.append(file.resolve())
        if system() == "Linux":
            # Linux has a shared modules path
            if not _path["modules_system"]:
                _path["modules_system"] = _LINUX_SHARED_BASE / "modules"
            if _path["modules_system"].is_dir():
                for file_ in _path["modules_system"].iterdir():
                    if file_.name.endswith(mod_ext) and file_.name not in user_modules_file_names:
                        _modules.append(file_.resolve())
    return _modules


def get_resources_path(file_name: str) -> Path:
    """Get full path of a resource file.

    Args:
        file_name (str): The filename to get

    Raises:
        FileNotFoundError: When no such file

    Returns:
        Path: The full path
    """
    if not _path["resources_user"]:
        _path["resources_user"] = get_data_path("resources")
    user_override = _path["resources_user"] / file_name
    if user_override.exists():
        return user_override

    if system() == "Linux":
        # Linux has a system wide path to make package manager happy
        if not _path["resources_system"]:
            _path["resources_system"] = _LINUX_SHARED_BASE / "resources"
        system_wide = _path["resources_system"] / file_name
        if system_wide.exists():
            return system_wide

    # Those files are in the /resources folder
    with resource_as_file(resource_files("autoxuexiplaywright") / "resources" / file_name) as path:
        if path.exists():
            return path.resolve()

    raise FileNotFoundError("No such file: " + file_name)


def _get_data_home() -> Path:
    """Get data storage path.

    Returns:
        Path: The full path to store data
    """
    match system():
        case "Windows":
            path = Path.home() / "AppData" / "Local" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
        case "Linux":
            xdg_data_home = environ.get("XDG_DATA_HOME")
            xdg_data_home = (
                Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
            )
            app_data = xdg_data_home / APPNAME
            app_data.mkdir(parents=True, exist_ok=True)
            return app_data
        case "Darwin":
            path = Path.home() / "Library" / "Application Support" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
        case _:
            path = Path.home() / ".local" / "share" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path


def _get_config_home() -> Path:
    """Get config storage path.

    Returns:
        Path: The full path to store config
    """
    match system():
        case "Windows":
            path = Path.home() / "AppData" / "Local" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
        case "Linux":
            xdg_config_home = environ.get("XDG_CONFIG_HOME")
            xdg_config_home = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
            app_config = xdg_config_home / APPNAME
            app_config.mkdir(parents=True, exist_ok=True)
            return app_config
        case "Darwin":
            path = Path.home() / "Library" / "Preferences" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
        case _:
            path = Path.home() / ".config" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path


def _get_cache_home() -> Path:
    """Get cache storage path.

    Returns:
        Path: The full path to store config
    """
    match system():
        case "Windows":
            path = Path.home() / "AppData" / "Local" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
        case "Linux":
            xdg_cache_home = environ.get("XDG_CACHE_HOME")
            xdg_cache_home = Path(xdg_cache_home) if xdg_cache_home else Path.home() / ".cache"
            app_cache = xdg_cache_home / APPNAME
            app_cache.mkdir(parents=True, exist_ok=True)
            return app_cache
        case "Darwin":
            path = Path.home() / "Library" / "Caches" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
        case _:
            path = Path.home() / ".cache" / APPNAME
            path.mkdir(parents=True, exist_ok=True)
            return path
