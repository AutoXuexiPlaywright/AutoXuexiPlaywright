from os import remove, walk, makedirs
from shutil import rmtree
from os.path import join, exists, expanduser
# Relative imports
from .common import cache, tasks_to_be_done, register_tasks, clean_tasks
from .common.answer.sources import load_all_answer_sources, close_all_answer_sources
from ..logger import warning
from ..config import get_runtime_config
from ..storage import get_cache_path
from ..languages import get_language_string


_config = get_runtime_config()
_legacy_pki_dir = join(expanduser("~"), ".pki")
_mozilla_dir = join(expanduser("~"), ".mozilla")
_remove_pki = not exists(_legacy_pki_dir)
_remove_mozilla = not exists(_mozilla_dir)


def _set_firefox_perf(perfs: dict[str, str | int | bool]):
    """Set firefox preferences

    Args:
        perfs(dict[str, str | int | bool]): The perferences dict
    """
    def construct_line(key: str, value: str | int | bool) -> str:
        """Build user.js line properly

        The string need to be quoted properly.

        Args:
            key(str): The preference key
            value(str | int | bool): The value of the key

        Returns:
            str: The proper line of user.js
        """
        if isinstance(value, str):
            value = "\"{value}\"".format(value=value)
        elif isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)
        return "user_pref(\"{key}\", {value});\n".format(key=key, value=value)

    profile_path = get_cache_path(join("browser-data", _config.browser_id))
    makedirs(profile_path, exist_ok=True)
    userjs_path = join(profile_path, "user.js")
    # user_pref("key", "str-value");
    # user_pref("key", 0);
    # user_pref("key", false);
    lines = [construct_line(key, value) for key, value in perfs.items()]
    with open(userjs_path, "w+", encoding="utf-8") as operator:
        file_lines = operator.readlines()
        changed = False
        for line in lines:
            if line not in file_lines:
                file_lines.append(line)
                changed = True
        if changed:
            operator.writelines(file_lines)


def _on_processor_started():
    """Called on processor started
    """
    cache.clear()
    tasks_to_be_done.clear()
    if _config.async_mode:
        from .async_api.test import DailyTestTask, WeeklyTestTask, SpecialTestTask
        from .async_api.login import LoginTask
        from .async_api.read import VideoTask, NewsTask
    else:
        from .sync_api.test import DailyTestTask, WeeklyTestTask, SpecialTestTask
        from .sync_api.login import LoginTask
        from .sync_api.read import VideoTask, NewsTask
    if not register_tasks(LoginTask, NewsTask, VideoTask, DailyTestTask, WeeklyTestTask, SpecialTestTask):
        warning(get_language_string("core-warning-register-task-failed"))
    load_all_answer_sources()
    if _config.browser_id == "firefox":
        _set_firefox_perf({"media.volume_scale": "0.0"})


def _on_processor_stopped():
    """Called when processor stopped
    """
    close_all_answer_sources()
    clean_tasks()
    tasks_to_be_done.clear()
    cache.clear()
    if not _config.debug:
        target_files = ("video.mp4", "qr.png", "video.m3u8", "cookies.json")
        for root, _, files in walk(get_cache_path("")):
            for file in files:
                file_path = join(root, file)
                if file_path.endswith(target_files):
                    remove(file_path)
        if _remove_mozilla and exists(_mozilla_dir):
            rmtree(_mozilla_dir)
        if _remove_pki and exists(_legacy_pki_dir):
            rmtree(_legacy_pki_dir)


def start_processor():
    """Start the processor
    """
    if _config.async_mode:
        from .async_api import start
    else:
        from .sync_api import start
    _on_processor_started()
    start()
    _on_processor_stopped()
