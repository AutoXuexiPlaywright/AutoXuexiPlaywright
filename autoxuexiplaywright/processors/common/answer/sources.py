from sqlite3 import connect
from abc import abstractmethod
from base64 import b64decode, b64encode
# Relative imports
from ..modules import get_modules_in_file, EXTRA_MODULES_NAMESPACE
from ...common import ANSWER_CONNECTOR
from ....sdk.answer import AnswerSource
from ....storage import get_modules_file_paths, get_data_path
from ....logger import debug, warning
from ....languages import get_language_string
from ....defines import APPAUTHOR


_ANSWER_DB_FILENAME = "data.db"
_ANSWER_SOURCE_MOD_EXT = ".as.py"
_ANSWER_SOURCE_NAMESPACE = EXTRA_MODULES_NAMESPACE+".answer_sources"

_answer_sources: list[AnswerSource] = []


class _AddSupportedAnswerSource(AnswerSource):
    @abstractmethod
    def add(self, title: str, answer: list[str]):
        pass


class SqliteAnswerSource(_AddSupportedAnswerSource):
    def start(self):
        self._conn = connect(get_data_path(_ANSWER_DB_FILENAME))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS 'answer' ('QUESTION' TEXT NOT NULL UNIQUE,'ANSWER' TEXT NOT NULL)")
        self._conn.commit()

    def get_answer(self, title: str) -> list[str]:
        title_encoded = b64encode(title.encode()).decode()
        answer = []
        answer_str_encoded = self._conn.execute(
            "SELECT ANSWER FROM 'answer' WHERE 'QUESTION'= ?", (title_encoded,)
        ).fetchone()
        if isinstance(answer_str_encoded, str):
            answer_str = b64decode(answer_str_encoded).decode()
            answer = answer_str.split(ANSWER_CONNECTOR)
        return answer

    def add(self, title: str, answer: list[str]):
        answer_str = ANSWER_CONNECTOR.join(answer)
        title_encoded = b64encode(title.encode()).decode()
        answer_str_encoded = b64encode(answer_str.encode()).decode()
        self._conn.execute(
            "INSERT OR REPLACE INTO 'answer' ('QUESTION', 'ANSWER') VALUES (?, ?)",
            (title_encoded, answer_str_encoded)
        )
        self._conn.commit()

    def close(self):
        self._conn.commit()
        self._conn.close()

    @property
    def name(self) -> str:
        return "SqliteAnswerSource"

    @property
    def author(self) -> str:
        return APPAUTHOR


def _add_source_manually(source: type[AnswerSource]):
    instance = source()
    if instance not in _answer_sources:
        instance.start()
        _answer_sources.append(instance)


def load_all_answer_sources():
    """Load all answer sources
    """
    for module_path in get_modules_file_paths(_ANSWER_SOURCE_MOD_EXT):
        debug(get_language_string("core-debug-loading-module-file") % module_path)
        modules = get_modules_in_file(
            module_path, _ANSWER_SOURCE_NAMESPACE)
        for module in modules:
            if isinstance(module, AnswerSource) and module not in _answer_sources:
                _answer_sources.append(module)
    _add_source_manually(SqliteAnswerSource)
    debug(get_language_string("core-debug-current-modules-num") %
          (len(_answer_sources), str(_answer_sources)))
    if len(_answer_sources) > 1:
        warning(get_language_string("core-warning-using-external-modules"))


def find_answer_in_answer_sources(title: str) -> list[str]:
    """Find first answer in answer sources

    Args:
        title (str): The question

    Returns:
        list[str]: The result, will be an empty list if no answer
    """
    for answer_source in _answer_sources:
        try:
            result = answer_source.get_answer(title)
        except Exception as e:
            debug(get_language_string("core-debug-answer-source-failed") %
                  (answer_source.author, answer_source.name, e))
        else:
            if len(result) > 0:
                return result
    return []


def add_answer_to_all_sources(title: str, answer: list[str]):
    """Add answer to all supported sources

    Args:
        title (str): The question title
        answer (list[str]): The question answer
    """
    for answer_source in _answer_sources:
        if isinstance(answer_source, _AddSupportedAnswerSource):
            try:
                answer_source.add(title, answer)
            except Exception as e:
                debug(get_language_string("core-debug-failed-to-add-answer") % e)


def close_all_answer_sources():
    """Close all answer sources
    """
    def try_close(answer_source: AnswerSource) -> bool:
        try:
            answer_source.close()
        except Exception as e:
            warning(get_language_string("core-warning-close-source-failed") % e)
            return True
        else:
            return False
    if len(list(filter(try_close, _answer_sources))) > 0:
        warning(get_language_string(
            "core-warning-exisis-sources-failed-to-close"))
