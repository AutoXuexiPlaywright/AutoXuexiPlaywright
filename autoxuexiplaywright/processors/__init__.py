"""Classes and functions for handling various tasks."""

from shutil import rmtree

# Relative imports
from .common import cache
from .common import clean_tasks
from .common import register_tasks
from .common import tasks_to_be_done
from pathlib import Path
from ..config import get_runtime_config
from ..logger import warning
from ..storage import get_cache_path
from ..storage import get_modules_file_paths
from ..languages import get_language_string
from .common.modules import load_modules
from .common.answer.sources import load_all_answer_sources
from .common.answer.sources import close_all_answer_sources


_config = get_runtime_config()
_legacy_pki_dir = Path.home() / ".pki"
_mozilla_dir = Path.home() / ".mozilla"
_remove_pki = not _legacy_pki_dir.exists()
_remove_mozilla = not _mozilla_dir.exists()

MODULE_EXT = ".py"


def _on_processor_started():
    """Called on processor started."""
    cache.clear()
    tasks_to_be_done.clear()
    if _config.async_mode:
        from .async_api.read import NewsTask
        from .async_api.read import VideoTask
        from .async_api.test import DailyTestTask
        from .async_api.test import WeeklyTestTask
        from .async_api.test import SpecialTestTask
        from .async_api.login import LoginTask
    else:
        from .sync_api.read import NewsTask
        from .sync_api.read import VideoTask
        from .sync_api.test import DailyTestTask
        from .sync_api.test import WeeklyTestTask
        from .sync_api.test import SpecialTestTask
        from .sync_api.login import LoginTask
    if not register_tasks(
        LoginTask,
        NewsTask,
        VideoTask,
        DailyTestTask,
        WeeklyTestTask,
        SpecialTestTask,
    ):
        warning(get_language_string("core-warning-register-task-failed"))
    for filename in get_modules_file_paths(MODULE_EXT):
        load_modules(filename)
    load_all_answer_sources()


def _on_processor_stopped():
    """Called when processor stopped."""
    close_all_answer_sources()
    clean_tasks()
    tasks_to_be_done.clear()
    cache.clear()
    if not _config.debug:
        target_files = ("video.mp4", "qr.png", "video.m3u8", "cookies.json")
        for f in get_cache_path("").iterdir():
            if f.name.endswith(target_files):
                f.unlink()
        if _remove_mozilla and _mozilla_dir.exists():
            rmtree(_mozilla_dir)
        if _remove_pki and _legacy_pki_dir.exists():
            rmtree(_legacy_pki_dir)


def start_processor():
    """Start the processor."""
    if _config.async_mode:
        from .async_api import start
    else:
        from .sync_api import start
    _on_processor_started()
    start()
    _on_processor_stopped()
