from json import load
from tempfile import mkdtemp
from os import chdir, rmdir, remove
from os.path import realpath, split, join
from autoxuexiplaywright.config import Config, deserialize_config, serialize_config


chdir(split(realpath(__file__))[0])

_input_config_instance_normal = Config()
_input_config_instance_normal.lang = "en-us"
_input_config_instance_normal.async_mode = True
_input_config_instance_normal.browser_id = "chromium"
_input_config_instance_normal.debug = False
_input_config_instance_normal.browser_channel = "msedge"
_input_config_instance_normal.executable_path = "/path/to/test"
_input_config_instance_normal.gui = False
_input_config_instance_normal.proxy = {"server": "127.0.0.1"}
_input_config_instance_normal.skipped = ["A", "B"]


_input_config_instance_nokey = Config()
_input_config_instance_nokey.lang = "en-us"


_input_config_instance_extrakey = Config()


_configs_map = {
    "normal.json": _input_config_instance_normal,
    "nokey.json": _input_config_instance_nokey,
    "extrakey.json": _input_config_instance_extrakey
}


def test_deserialize_config():
    for k, v in _configs_map.items():
        assert deserialize_config(join("data", k)) == v


def test_serialize_config():
    temp = mkdtemp()
    try:
        for k, v in _configs_map.items():
            tmp_path = join(temp, k)
            serialize_config(v, tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as reader:
                json = load(reader)
            assert v.__dict__ == json
    finally:
        [remove(join(temp, k)) for k in _configs_map.keys()]
        rmdir(temp)
