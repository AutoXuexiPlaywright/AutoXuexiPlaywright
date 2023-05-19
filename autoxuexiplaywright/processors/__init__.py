from os import remove, walk
from os.path import join
# Relative imports
from .common import cache, tasks_to_be_done, register_tasks, clean_tasks
from .common.answer.sources import load_all_answer_sources, close_all_answer_sources
from ..logger import warning
from ..config import get_runtime_config
from ..storage import get_cache_path
from ..languages import get_language_string


_config = get_runtime_config()


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


def _on_processor_stopped():
    """Called when processor stopped
    """
    close_all_answer_sources()
    clean_tasks()
    tasks_to_be_done.clear()
    cache.clear()
    if not _config.debug:
        target_files = ("video.mp4", "qr.png", "video.m3u8")
        for root, _, files in walk(get_cache_path("")):
            for file in files:
                file_path = join(root, file)
                if file_path.endswith(target_files):
                    remove(file_path)


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
