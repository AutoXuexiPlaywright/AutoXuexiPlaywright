import os
import json
from autoxuexiplaywright.utils import storage

__all__ = ["get_lang"]
_lang: dict[str, dict[str, str]] = {}


def get_lang(code: str, key: str) -> str:
    lang = _lang.get(code)
    if not isinstance(lang, dict):
        with open(storage.get_resource_path(os.path.join("lang", code+".json")), "r", encoding="utf-8") as reader:
            lang = json.load(reader)
        _lang.update(code=lang)
    lang_str = lang.get(key)
    if lang_str is None:
        raise Exception("No such key %s in language %s" % (key, code))
    return lang_str
