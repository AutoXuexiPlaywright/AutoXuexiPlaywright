"""Config struct."""

from json import dump
from json import load
from typing import Literal
from pathlib import Path
from playwright._impl._api_structures import ProxySettings


ChannelType = (
    Literal[
        "msedge",
        "msedge-beta",
        "msedge-dev",
        "chrome",
        "chrome-beta",
        "chrome-dev",
        "chromium",
        "chromium-beta",
        "chromium-dev",
    ]
    | None
)
BrowserType = Literal["firefox", "chromium", "webkit"]


class Config:
    """class for storaging runtime config."""

    def __init__(self) -> None:
        """Initialize default config."""
        self.lang = "zh-cn"
        self.async_mode = False
        self.browser_id: BrowserType = "firefox"
        self.browser_channel: ChannelType = None
        self.debug = False
        self.executable_path: str | None = None
        self.gui = True
        self.proxy: ProxySettings | None = None
        self.skipped: list[str] = []
        self.get_video = False

    def __eq__(self, __o: object) -> bool:
        """Compare equality."""
        return isinstance(__o, Config) and (self.__dict__ == __o.__dict__)

    def __hash__(self) -> int:
        """Hash object."""
        return hash(self.__dict__)


_configs: dict[Path | Literal["_"], Config] = {}


def set_runtime_config(config: Config):
    """Set config as runtime config.

    Args:
        config (Config): The config to be set
    """
    _configs["_"] = config


def get_runtime_config() -> Config:
    """Get the runtime config set.

    Returns:
        Config: The runtime config
    """
    return _configs["_"] if "_" in _configs else Config()


def deserialize_config(path: Path) -> Config:
    """Deserialize config to config instance.

    **Note**: `path="_"` means runtime config

    Args:
        path (Path): The path to config

    Returns:
        Config: The config instance
    """
    if path not in _configs:
        with Path(path).open("r", encoding="utf-8") as reader:
            config_json = load(reader)
        if path.name != "_":
            _configs[path] = _deserialize_config_from_json(config_json)
    return _configs[path]


def serialize_config(config: Config, path: Path, indent: int = 4, sort_keys: bool = True):
    """Serialize config instance to path.

    **Note**: `path="_"` will be skipped because it is runtime config

    Args:
        config (Config): The config instance
        path (Path): The path to config
        indent (int, optional): The number of json indent. Defaults to 4.
        sort_keys (bool, optional): If sort json keys. Defaults to True.
    """
    if path.name == "_":
        return
    with path.open("w", encoding="utf-8") as writer:
        dump(_serialize_config_to_json(config), writer, indent=indent, sort_keys=sort_keys)


def _deserialize_config_from_json(json: dict[str, bool | str | ProxySettings | None]) -> Config:
    """Create a config instance and apply json to it.

    Args:
        json (dict[str, bool  |  str  |  ProxySettings  |  None]): The json dict

    Returns:
        Config: The config instance
    """
    config = Config()
    for key, value in json.items():
        if hasattr(config, key):
            match key:
                case "lang":
                    if isinstance(value, str):
                        config.lang = value
                case "async_mode":
                    if isinstance(value, bool):
                        config.async_mode = value
                case "browser_id":
                    if isinstance(value, str):
                        match value:
                            case "firefox" | "chromium" | "webkit":
                                config.browser_id = value
                            case _:
                                pass
                case "browser_channel":
                    if isinstance(value, str):
                        match value:
                            case (
                                "msedge"
                                | "msedge-beta"
                                | "msedge-dev"
                                | "chromium"
                                | "chromium-beta"
                                | "chromium-dev"
                                | "chrome"
                                | "chrome-beta"
                                | "chrome-dev"
                            ):
                                config.browser_channel = value
                            case _:
                                pass
                case "debug":
                    if isinstance(value, bool):
                        config.debug = value
                case "executable_path":
                    if isinstance(value, str):
                        config.executable_path = value
                case "gui":
                    if isinstance(value, bool):
                        config.gui = value
                case "proxy":
                    if isinstance(value, dict):
                        config.proxy = value
                case "skipped":
                    if isinstance(value, list):
                        config.skipped = value
                case "get_video":
                    if isinstance(value, bool):
                        config.get_video = value
                case _:
                    pass

    return config


def _serialize_config_to_json(config: Config) -> dict[str, bool | str | ProxySettings | None]:
    """Convert a config instance to json dict.

    Args:
        config (Config): The config instance

    Returns:
        dict[str, bool | str | ProxySettings | None]: The json dict
    """
    return config.__dict__
