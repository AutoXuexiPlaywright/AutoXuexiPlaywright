"""AutoxuexiPlaywright main module."""

# Relative imports
from .config import Config
from .config import serialize_config
from .config import deserialize_config
from .config import get_runtime_config
from .config import set_runtime_config
from pathlib import Path
from .storage import get_config_path
from argparse import ArgumentParser
from argparse import BooleanOptionalAction


def main():
    """Entrance of program."""
    parser = ArgumentParser()
    _ = parser.add_argument(
        "--gui",
        "-g",
        action=BooleanOptionalAction,
        help="If enable GUI mode by force",
        dest="gui",
    )
    _ = parser.add_argument(
        "--config",
        "-c",
        action="store",
        help='The config file path, "_" will be skipped',
        dest="config",
    )
    args = parser.parse_args()
    # apply args
    if isinstance(args.config, str):
        # config path in args and file exists
        config_path = Path(args.config)
        save = not Path(args.config).is_file() or (args.config == "_")
    elif Path("config.json").is_file():
        # current directory has a config path
        config_path = Path("config.json")
        save = False
    else:
        # default config path and file exists
        config_path = get_config_path("config.json")
        save = not get_config_path("config.json").is_file()
    # load porper config
    if save:
        default_runtime_config = Config()
        set_runtime_config(default_runtime_config)
        serialize_config(default_runtime_config, config_path)
    else:
        set_runtime_config(deserialize_config(config_path))
    if isinstance(args.gui, bool):
        get_runtime_config().gui = args.gui

    if get_runtime_config().gui:
        from autoxuexiplaywright.gui import start
        from autoxuexiplaywright.gui import register_callbacks
    else:
        from autoxuexiplaywright.core import start
        from autoxuexiplaywright.core import register_callbacks
    register_callbacks()
    start()
