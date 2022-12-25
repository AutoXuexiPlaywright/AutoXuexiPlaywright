from os.path import isfile
from json import load, dump
from playwright._impl._api_structures import ProxySettings

from autoxuexiplaywright.defines.core import DEFAULT_CONF, ANSWER_CONNECTOR
from autoxuexiplaywright.defines.types import ConfigType
from autoxuexiplaywright.utils.storage import get_config_path


class Config:
    instance = None

    @staticmethod
    def get_instance(path: str | None = None, refresh: bool = False):
        if (not isinstance(Config.instance, Config)) or refresh:
            Config.instance = Config(path)
        return Config.instance

    def __init__(self, path: str | None = None):
        if path == None:
            path = get_config_path("config.json")
        json: ConfigType = {}
        if isfile(path):
            with open(path, "r", encoding="utf-8") as reader:
                json.update(**load(reader))
        else:
            json.update(DEFAULT_CONF)
            with open(path, "w", encoding="utf-8") as writer:
                dump(DEFAULT_CONF, writer, indent=4, sort_keys=True)

        # Prepare variables and make sure their types are correct
        # This is for passing the type check:

        # Language
        lang = json.get("lang", "zh-cn")
        assert isinstance(lang, str)
        self.lang = lang
        # Async API
        async_mode = json.get("async", False)
        assert isinstance(async_mode, bool)
        self.async_mode = async_mode
        # Browser
        browser_id = json.get("browser", "firefox")
        assert isinstance(browser_id, str)
        self.browser_id = browser_id
        # Channel
        channel = json.get("channel", None)
        assert isinstance(channel, str | None)
        self.channel = channel
        # Debug mode
        debug = json.get("debug", False)
        assert isinstance(debug, bool)
        self.debug = debug
        # Browser executable
        executable_path = json.get("executable_path", None)
        assert isinstance(executable_path, str | None)
        self.executable_path = executable_path
        # GUI mode
        gui = json.get("gui", True)
        assert isinstance(gui, bool)
        self.gui = gui
        # Proxy
        proxy = json.get("proxy", None)
        assert isinstance(proxy, dict | None)
        self.proxy: ProxySettings | None = proxy
        # Skipped
        skipped = json.get("skipped_items", None)
        assert isinstance(skipped, str | None)
        self.skipped = skipped.split(
            ANSWER_CONNECTOR) if skipped is not None else []
