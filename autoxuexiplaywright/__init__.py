from os.path import isfile
from argparse import ArgumentParser, BooleanOptionalAction
# Relative imports
from .config import Config, deserialize_config, serialize_config, set_runtime_config, get_runtime_config
from .storage import get_config_path


def main():
    parser = ArgumentParser()
    parser.add_argument("--gui", "-g", action=BooleanOptionalAction,
                        help="If enable GUI mode by force", dest="gui")
    parser.add_argument(
        "--config", "-c", action="store", help="The config file path, \"_\" will be skipped", dest="config")
    args = parser.parse_args()
    # apply args
    if isinstance(args.config, str) and isfile(args.config):
        # config path in args and file exists
        config_path = args.config
        save = False
    elif isinstance(args.config, str) and (args.config != "_"):
        # config path in args but not exists
        config_path = args.config
        save = True
    elif isfile("config.json"):
        # current directory has a config path
        config_path = "config.json"
        save = False
    elif isfile(get_config_path("config.json")):
        # default config path and file exists
        config_path = get_config_path("config.json")
        save = False
    else:
        # create new config at default path
        config_path = get_config_path("config.json")
        save = True
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
        from autoxuexiplaywright.gui import start, register_callbacks
    else:
        from autoxuexiplaywright.core import start, register_callbacks
    register_callbacks()
    start()
