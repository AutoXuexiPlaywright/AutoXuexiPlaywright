"""Classes and functions of Language module."""

from json import load

# Relative imports
from .config import get_runtime_config
from .storage import get_resources_path


_languages: dict[str, dict[str, str]] = {}


class NoSuchLanguageKeyException(Exception):
    """Exception shows that no language string with given key."""
    def __init__(self, key: str) -> None:
        """Initialize a NoSuchLanguageKeyException instance.

        Args:
            key(str): The language key which has no language string
        """
        self.key = key
        super().__init__("No such language key %s" % key)


def _get_language(lang: str | None = None) -> dict[str, str]:
    if not lang:
        lang = get_runtime_config().lang
    if lang not in _languages:
        language_file = get_resources_path("lang") / (lang + ".json")
        with language_file.open("r", encoding="utf-8") as reader:
            language_dict = load(reader)
        _languages[lang] = language_dict
    return _languages[lang]


def get_language_string(key: str, lang: str | None = None) -> str:
    """Get localized language value by key.

    Args:
        key (str): The key to get
        lang (str | None, optional): The language id, None means current language. Defaults to None.

    Raises:
        NoSuchLanguageKeyException: When no such key in language dict/file

    Returns:
        str: The localized value
    """
    language = _get_language(lang)
    if key in language:
        return language[key]
    raise NoSuchLanguageKeyException(key)
