"""Test if deserialize and serialize are correct."""

from json import load
from pathlib import Path
from autoxuexiplaywright.config import Config
from autoxuexiplaywright.config import serialize_config
from autoxuexiplaywright.config import deserialize_config


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
    "extrakey.json": _input_config_instance_extrakey,
}


def test_deserialize_config():
    """Check if deserialize_config works."""
    file_dir = Path(__file__).resolve().parent
    for k, v in _configs_map.items():
        assert deserialize_config(file_dir / "data" / k) == v


def test_serialize_config(tmpdir: str):
    """Check if serialize_config works."""
    for k, v in _configs_map.items():
        tmp_path = Path(tmpdir) / k
        serialize_config(v, tmp_path)
        with tmp_path.open("r", encoding="utf-8") as reader:
            json = load(reader)
        assert v.__dict__ == json
