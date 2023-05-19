from json import load
from os.path import join
# Relative imports
from .config import get_runtime_config
from .storage import get_resources_path

_languages: dict[str, dict[str, str]] = {}


class NoSuchLanguageKeyException(Exception):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__("No such language key %s" % key)


def _get_language(lang: str | None = None) -> dict[str, str]:
    if lang == None:
        lang = get_runtime_config().lang
    if lang not in _languages.keys():
        langage_file = get_resources_path(join("lang", lang+".json"))
        with open(langage_file, "r", encoding="utf-8") as reader:
            language_dict = load(reader)
        _languages[lang] = language_dict
    return _languages[lang]


def get_language_string(key: str, lang: str | None = None) -> str:
    """Get localized language value by key

    Args:
        key (str): The key to get
        lang (str | None, optional): The language id, None means current language. Defaults to None.

    Raises:
        NoSuchLanguageKeyException: When no such key in language dict/file

    Returns:
        str: The localized value
    """
    language = _get_language(lang)
    if key in language.keys():
        return language[key]
    raise NoSuchLanguageKeyException(key)
