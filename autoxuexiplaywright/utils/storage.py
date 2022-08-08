import os
import platform
from importlib import resources
from autoxuexiplaywright.defines import core

__all__ = ["get_resource_path", "get_cache_path",
           "get_config_path", "get_modules_paths"]
global CACHE_DIR
global CONF_DIR
global DATA_DIR


def get_resource_path(file_name: str) -> str:
    user_override = os.path.join(DATA_DIR, "resources", file_name)
    with resources.path("autoxuexiplaywright", "resources") as path:
        system_default = str(path/file_name)
    if os.path.exists(user_override):
        return user_override
    elif os.path.exists(system_default):
        return system_default

    raise FileNotFoundError


def get_cache_path(file_name: str) -> str:
    return os.path.join(CACHE_DIR, file_name)


def get_config_path(file_name: str) -> str:
    return os.path.join(CONF_DIR, file_name)


def get_data_path(file_name: str) -> str:
    user_override = os.path.join(DATA_DIR, file_name)
    linux_system_shared = "/usr/share/autoxuexiplaywright/"+file_name
    if os.path.exists(user_override):
        return user_override
    elif platform.system() == "Linux" and os.path.exists(linux_system_shared):
        return linux_system_shared
    raise FileNotFoundError


def get_modules_paths() -> list[str]:
    modules_paths = []
    user_override = os.path.join(DATA_DIR, "modules")
    linux_system_shared = "/usr/share/autoxuexiplaywright/modules"
    user_module_files = [file for file in os.listdir(
        user_override) if file.endswith(core.MOD_EXT)] if os.path.isdir(user_override) else []
    system_module_files = [file for file in os.listdir(linux_system_shared) if file.endswith(
        core.MOD_EXT)] if platform.system() == "Linux" and os.path.isdir(linux_system_shared) else []
    for file in system_module_files:
        if file not in user_module_files:
            modules_paths.append(os.path.join(linux_system_shared, file))
    modules_paths += [os.path.join(user_override, file)
                      for file in user_module_files]
    return modules_paths


system = platform.system()
if system == "Linux":
    from xdg import BaseDirectory
    DATA_DIR = BaseDirectory.save_data_path(core.APPID)
    CONF_DIR = BaseDirectory.save_config_path(core.APPID)
    CACHE_DIR = BaseDirectory.save_cache_path(core.APPID)
elif system == "Windows":
    DATA_DIR = os.path.join(os.path.expanduser(
        "~"), "AppData", "Local", core.APPID)
    CONF_DIR = os.path.join(os.path.expanduser(
        "~"), "AppData", "Local", core.APPID)
    CACHE_DIR = os.path.join(os.path.expanduser("~"),
                             "AppData", "Local", core.APPID)
elif system == "Darwin":
    DATA_DIR = os.path.join(os.path.expanduser(
        "~"), "Library", "Application Support", core.APPID)
    CONF_DIR = os.path.join(os.path.expanduser(
        "~"), "Library", "Preferences", core.APPID)
    CACHE_DIR = os.path.join(os.path.expanduser("~"),
                             "Library", "Caches", core.APPID)
else:
    DATA_DIR = os.path.join(os.path.expanduser(
        "~"), ".local", "share", core.APPID)
    CONF_DIR = os.path.join(os.path.expanduser("~"), ".config", core.APPID)
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", core.APPID)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONF_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
