import os
import json
from typing import Union
from autoxuexiplaywright.defines import core
from autoxuexiplaywright.utils import storage


def get_runtime_config() -> dict[str, Union[bool, str, list[dict[str, str]]]]:
    conf_path = storage.get_config_path("config.json")
    if os.path.isfile(conf_path):
        with open(conf_path, "r", encoding="utf-8") as reader:
            return json.load(reader)
    else:
        with open(conf_path, "w", encoding="utf-8") as writer:
            json.dump(core.DEFAULT_CONF, writer, indent=4, sort_keys=True)
        return core.DEFAULT_CONF
