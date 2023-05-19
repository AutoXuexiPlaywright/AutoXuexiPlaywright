from os.path import join
from json import load
from autoxuexiplaywright.languages import get_language_string, NoSuchLanguageKeyException
from autoxuexiplaywright.config import Config, set_runtime_config
from autoxuexiplaywright.storage import get_resources_path


def test_language_string():
    set_runtime_config(Config())  # lang="zh-cn"
    with open(get_resources_path(join("lang", "zh-cn.json")), "r", encoding="utf-8") as reader:
        language_json: dict[str, str] = load(reader)
    for key in language_json.keys():
        assert get_language_string(key) == language_json[key]
    try:
        get_language_string("key-not-exist")
    except NoSuchLanguageKeyException:
        pass
    else:
        raise Exception
