from queue import Queue
from base64 import b64decode, b64encode
from random import sample
from string import ascii_letters, digits
from logging import getLogger
from sqlite3 import connect
from enum import Enum
from importlib import util
from autoxuexiplaywright.defines.core import APPID, ANSWER_CONNECTOR, EXTRA_ANSWER_SOURCES_NAMESPACE, MOD_EXT
from autoxuexiplaywright.defines.events import EventId
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.storage import get_config_path, get_modules_paths
from autoxuexiplaywright.utils.eventmanager import find_event_by_id
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.sdk import AnswerSource


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
        self.author = APPID
        self.priority = 0
        self.conn = connect(get_config_path("data.db"))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS 'answer' ('QUESTION' TEXT NOT NULL UNIQUE,'ANSWER' TEXT NOT NULL)")
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def add_answer(self, title: str, answer: list[str]) -> None:
        answer_str = ANSWER_CONNECTOR.join(answer)
        title_encooded = b64encode(title.encode()).decode()
        answer_str_encoded = b64encode(answer_str.encode()).decode()
        self.conn.execute("INSERT OR REPLACE INTO 'answer' ('QUESTION', 'ANSWER') VALUES (?, ?)",
                          (title_encooded, answer_str_encoded))
        self.conn.commit()

    def get_answer(self, title: str) -> list[str]:
        title_encoded = b64encode(title.encode()).decode()
        answer = []
        answer_str_encoded = self.conn.execute(
            "SELECT ANSWER FROM 'answer' WHERE 'QUESTION'= ?", (title_encoded,)).fetchone()
        if answer_str_encoded is not None:
            answer_str_encoded = str(answer_str_encoded[0])
            answer_str = b64decode(answer_str_encoded).decode()
            answer = answer_str.split(ANSWER_CONNECTOR)
        return answer


def gen_random_str(length: int = 4) -> str:
    return "".join(sample(ascii_letters+digits, length))


def has_chinese_char(chars: str) -> bool:
    return any(["\u4e00" < char < "\u9fa5" for char in chars])


def has_alpha_or_num(chars: str) -> bool:
    return any([char in ascii_letters+digits for char in chars])


def is_valid_answer(chars: str) -> bool:
    return (has_chinese_char(chars) or has_alpha_or_num(chars))


def request_answer(tips: str) -> list[str]:
    answer: list[str] = []
    config = Config()
    if config.gui:
        # gui is ready for getting answer from user input
        answer_queue: Queue[list[str]] = Queue(1)
        find_event_by_id(
            EventId.ANSWER_REQUESTED).invoke(tips, answer_queue)
        answer = answer_queue.get()
    else:
        # headless mode
        answer = input(get_lang(config.lang, "core-manual-enter-answer-required") %
                       (ANSWER_CONNECTOR, tips)).strip().split(ANSWER_CONNECTOR)
    return answer


def init_sources() -> None:
    config = Config()
    sources.clear()
    sources.append(DatabaseSource())
    modules = get_modules_paths()
    if len(modules) > 0:
        getLogger(APPID).warning(get_lang(
            config.lang, "core-warning-using-external-modules"))
        priority = 1
        for file in modules:
            if file.endswith(MOD_EXT):
                try:
                    spec = util.spec_from_file_location(
                        EXTRA_ANSWER_SOURCES_NAMESPACE +
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
        sources.sort(key=lambda o: o.priority)
    if len(sources) > 0:
        getLogger(APPID).debug(get_lang(config.lang, "core-debug-current-modules-num") %
                               (len(sources), [src.name for src in sources]))


def close_sources() -> None:
    for source in sources:
        try:
            source.close()
        except:
            pass
        sources.remove(source)


def get_answer_from_sources(title: str) -> list[str]:
    for source in sources:
        try:
            result = source.get_answer(title)
        except Exception as e:
            getLogger(APPID).debug(get_lang(
                Config().lang, "core-debug-answer-source-failed") % (source.author, source.name, e))
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


__all__ = ["gen_random_str", "is_valid_answer", "request_answer",
           "init_sources", "close_sources", "get_answer_from_sources"]
