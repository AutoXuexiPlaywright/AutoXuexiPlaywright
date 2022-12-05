from os.path import isfile
from json import load, dump
from typing import Union
from autoxuexiplaywright.defines.core import DEFAULT_CONF
from autoxuexiplaywright.utils.storage import get_config_path


def get_runtime_config() -> dict[str, Union[bool, str, list[dict[str, str]]]]:
    conf_path = get_config_path("config.json")
    if isfile(conf_path):
        with open(conf_path, "r", encoding="utf-8") as reader:
            return load(reader)
    else:
        with open(conf_path, "w", encoding="utf-8") as writer:
            dump(DEFAULT_CONF, writer, indent=4, sort_keys=True)
        return DEFAULT_CONF
