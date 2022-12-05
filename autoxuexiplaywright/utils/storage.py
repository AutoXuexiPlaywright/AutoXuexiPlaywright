from os import listdir, makedirs
from os.path import join, exists, isdir, expanduser
from platform import system
from importlib import resources

from autoxuexiplaywright.defines.core import MOD_EXT, APPID


global CACHE_DIR
global CONF_DIR
global DATA_DIR


def get_resource_path(file_name: str) -> str:
    user_override = join(DATA_DIR, "resources", file_name)
    with resources.path("autoxuexiplaywright", "resources") as path:
        system_default = str(path/file_name)
    if exists(user_override):
        return user_override
    elif exists(system_default):
        return system_default

    raise FileNotFoundError


def get_cache_path(file_name: str) -> str:
    return join(CACHE_DIR, file_name)


def get_config_path(file_name: str) -> str:
    return join(CONF_DIR, file_name)


def get_data_path(file_name: str) -> str:
    user_override = join(DATA_DIR, file_name)
    linux_system_shared = "/usr/share/autoxuexiplaywright/"+file_name
    if exists(user_override):
        return user_override
    elif (system() == "Linux") and exists(linux_system_shared):
        return linux_system_shared
    raise FileNotFoundError


def get_modules_paths() -> list[str]:
    modules_paths = []
    user_override = join(DATA_DIR, "modules")
    linux_system_shared = "/usr/share/autoxuexiplaywright/modules"
    user_module_files = [file for file in listdir(
        user_override) if file.endswith(MOD_EXT)] if isdir(user_override) else []
    system_module_files = [file for file in listdir(linux_system_shared) if file.endswith(
        MOD_EXT)] if system() == "Linux" and isdir(linux_system_shared) else []
    for file in system_module_files:
        if file not in user_module_files:
            modules_paths.append(join(linux_system_shared, file))
    modules_paths += [join(user_override, file)
                      for file in user_module_files]
    return modules_paths


match system():
    case "Linux":
        from xdg import BaseDirectory
        DATA_DIR = BaseDirectory.save_data_path(APPID)
        CONF_DIR = BaseDirectory.save_config_path(APPID)
        CACHE_DIR = BaseDirectory.save_cache_path(APPID)
    case "Windows":
        DATA_DIR = join(expanduser(
            "~"), "AppData", "Local", APPID)
        CONF_DIR = join(expanduser(
            "~"), "AppData", "Local", APPID)
        CACHE_DIR = join(expanduser("~"),
                        "AppData", "Local", APPID)
    case "Darwin":
        DATA_DIR = join(expanduser(
            "~"), "Library", "Application Support", APPID)
        CONF_DIR = join(expanduser(
            "~"), "Library", "Preferences", APPID)
        CACHE_DIR = join(expanduser("~"),
                        "Library", "Caches", APPID)
    case default:
        DATA_DIR = join(expanduser(
            "~"), ".local", "share", APPID)
        CONF_DIR = join(expanduser("~"), ".config", APPID)
        CACHE_DIR = join(expanduser("~"), ".cache", APPID)
makedirs(DATA_DIR, exist_ok=True)
makedirs(CONF_DIR, exist_ok=True)
makedirs(CACHE_DIR, exist_ok=True)

__all__ = ["get_resource_path", "get_cache_path",
           "get_config_path", "get_modules_paths"]
