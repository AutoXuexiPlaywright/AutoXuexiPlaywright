from autoxuexiplaywright.config import Config, get_runtime_config, set_runtime_config

_config = Config()


def test_set_runtime_config():
    set_runtime_config(_config)


def test_get_runtime_config():
    set_runtime_config(_config)
    assert get_runtime_config() == _config
