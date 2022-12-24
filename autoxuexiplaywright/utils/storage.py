from os import listdir, makedirs
from os.path import join, exists, isdir, expanduser
from platform import system
from importlib import resources

from autoxuexiplaywright.defines.core import MOD_EXT

from autoxuexiplaywright import appid


def get_resource_path(file_name: str) -> str:
    user_override = join(data_dir, "resources", file_name)
    with resources.path("autoxuexiplaywright", "resources") as path:
        system_default = str(path/file_name)
    if exists(user_override):
        return user_override
    elif exists(system_default):
        return system_default

    raise FileNotFoundError


def get_cache_path(file_name: str) -> str:
    return join(cache_dir, file_name)


def get_config_path(file_name: str) -> str:
    return join(conf_dir, file_name)


def get_data_path(file_name: str) -> str:
    user_override = join(data_dir, file_name)
    linux_system_shared = "/usr/share/autoxuexiplaywright/"+file_name
    if exists(user_override):
        return user_override
    elif (system() == "Linux") and exists(linux_system_shared):
        return linux_system_shared
    raise FileNotFoundError


def get_modules_paths() -> list[str]:
    modules_paths: list[str] = []
    user_override = join(data_dir, "modules")
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
        from xdg import BaseDirectory  # type: ignore
        data_dir = BaseDirectory.save_data_path(appid)  # type: ignore
        conf_dir = BaseDirectory.save_config_path(appid)  # type: ignore
        cache_dir = BaseDirectory.save_cache_path(appid)  # type: ignore
    case "Windows":
        data_dir = join(expanduser(
            "~"), "AppData", "Local", appid)
        conf_dir = join(expanduser(
            "~"), "AppData", "Local", appid)
        cache_dir = join(expanduser("~"),
                         "AppData", "Local", appid)
    case "Darwin":
        data_dir = join(expanduser(
            "~"), "Library", "Application Support", appid)
        conf_dir = join(expanduser(
            "~"), "Library", "Preferences", appid)
        cache_dir = join(expanduser("~"),
                         "Library", "Caches", appid)
    case default:
        data_dir = join(expanduser(
            "~"), ".local", "share", appid)
        conf_dir = join(expanduser("~"), ".config", appid)
        cache_dir = join(expanduser("~"), ".cache", appid)
makedirs(data_dir, exist_ok=True)
makedirs(conf_dir, exist_ok=True)
makedirs(cache_dir, exist_ok=True)

__all__ = ["get_resource_path", "get_cache_path",
           "get_config_path", "get_modules_paths"]
