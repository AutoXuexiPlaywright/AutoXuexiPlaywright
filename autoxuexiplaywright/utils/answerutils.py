import base64
from inspect import isclass
import random
import string
import logging
import sqlite3
from enum import Enum
from importlib import util
from autoxuexiplaywright.defines import core
from autoxuexiplaywright.utils import lang, storage
from autoxuexiplaywright.sdk import AnswerSource, PRIORITY_INF


__all__ = ["gen_random_str", "is_valid_answer", "request_answer",
           "init_sources", "close_sources", "get_answer_from_sources"]
sources: list[AnswerSource] = []


class QuestionType(Enum):
    UNKNOWN = 0
    CHOICE = 1
    BLANK = 2


class AddSupportedAnswerSource(AnswerSource):
    def add_answer(self, title: str, answer: list[str]) -> None:
        pass


class DatabaseSource(AddSupportedAnswerSource):
    def __init__(self) -> None:
        self.name = "DatabaseSource"
        self.author = core.APPID
        self.priority = 0
        self.conn = sqlite3.connect(storage.get_config_path("data.db"))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS 'answer' ('QUESTION' TEXT NOT NULL UNIQUE,'ANSWER' TEXT NOT NULL)")
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def add_answer(self, title: str, answer: list[str]) -> None:
        answer_str = core.ANSWER_CONNECTOR.join(answer)
        title_encooded = base64.b64encode(title.encode()).decode()
        answer_str_encoded = base64.b64encode(answer_str.encode()).decode()
        self.conn.execute("INSERT OR REPLACE INTO 'answer' ('QUESTION', 'ANSWER') VALUES (?, ?)",
                          (title_encooded, answer_str_encoded))
        self.conn.commit()

    def get_answer(self, title: str) -> list[str]:
        title_encoded = base64.b64encode(title.encode()).decode()
        answer = []
        answer_str_encoded = self.conn.execute(
            "SELECT ANSWER FROM 'answer' WHERE 'QUESTION'= ?", (title_encoded,)).fetchone()
        if answer_str_encoded is not None:
            answer_str_encoded = str(answer_str_encoded[0])
            answer_str = base64.b64decode(answer_str_encoded).decode()
            answer = answer_str.split(core.ANSWER_CONNECTOR)
        return answer


def gen_random_str(length: int = 4) -> str:
    return "".join(random.sample(string.ascii_letters+string.digits, length))


def has_chinese_char(chars: str) -> bool:
    return any(["\u4e00" < char < "\u9fa5" for char in chars])


def has_alpha_or_num(chars: str) -> bool:
    return any([char in string.ascii_letters+string.digits for char in chars])


def is_valid_answer(chars: str) -> bool:
    return (has_chinese_char(chars) or has_alpha_or_num(chars))


def request_answer(tips: str, **kwargs) -> list[str]:
    answer = []
    mutex = kwargs.get("mutex")
    wait = kwargs.get("wait")
    answer_queue = kwargs.get("answer_queue")
    pause_thread_signal = kwargs.get("pause_thread_signal")
    if kwargs.get("gui", True) and (mutex is not None) and (wait is not None) and \
            (answer_queue is not None) and (pause_thread_signal is not None):
        # gui is ready for getting answer from user input
        mutex.lock()
        pause_thread_signal.emit(tips)
        wait.wait(mutex)
        answer = answer_queue.get()
        mutex.unlock()
    elif not kwargs.get("gui", True):
        # headless mode
        answer = input(lang.get_lang(kwargs.get("lang", "zh-cn"), "core-manual-enter-answer-required") %
                       (core.ANSWER_CONNECTOR, tips)).strip().split(core.ANSWER_CONNECTOR)
    else:
        logging.getLogger(core.APPID).error(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-error-no-way-to-get-manual-input"))
    return answer


def init_sources(**kwargs) -> None:
    sources.clear()
    sources.append(DatabaseSource())
    modules = storage.get_modules_paths()
    if len(modules) > 0:
        logging.getLogger(core.APPID).warning(lang.get_lang(
            kwargs.get("lang", "zh-cn"), "core-warning-using-external-modules"))
        priority = 1
        for file in modules:
            if file.endswith(core.MOD_EXT):
                try:
                    spec = util.spec_from_file_location(
                        core.EXTRA_ANSWER_SOURCES_NAMESPACE +
                        ".external_" + str(priority), file)
                    if spec is not None:
                        module = util.module_from_spec(spec)
                        if spec.loader is not None:
                            # WARN: This will execute the .as.py file and may result in unexpected behavior
                            spec.loader.exec_module(module)
                            for name in dir(module):
                                obj = getattr(module, name)
                                if issubclass(obj, AnswerSource) and not \
                                    issubclass(obj, AddSupportedAnswerSource) and not \
                                    obj is AnswerSource:
                                    instance = obj()
                                    instance.priority = priority
                                    sources.append(instance)
                                    priority += 1
                except:
                    pass

    if len(sources) > 1:
        sources.sort(key=lambda o: o.priority if isinstance(
            o, AnswerSource) else PRIORITY_INF)
    if len(sources) > 0:
        logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
            "lang", "zh-cn"), "core-debug-current-modules-num") % (len(sources), [src.name for src in sources]))


def close_sources() -> None:
    for source in sources:
        try:
            source.close()
        except:
            pass
        sources.remove(source)


def get_answer_from_sources(title: str, **kwargs) -> list[str]:
    for source in sources:
        try:
            result = source.get_answer(title)
        except Exception as e:
            logging.getLogger(core.APPID).debug(lang.get_lang(kwargs.get(
                "lang", "zh-cn"), "core-debug-answer-source-failed") % (source.author, source.name, e))
        else:
            if len(result) > 0:
                return result
    return []


def add_answer(title: str, answer: list[str]) -> None:
    for source in sources:
        if isinstance(source, AddSupportedAnswerSource):
            try:
                source.add_answer(title, answer)
            except:
                pass
