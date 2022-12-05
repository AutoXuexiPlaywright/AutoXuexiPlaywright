from os import chdir
from os.path import split, realpath
from sys import argv
from argparse import ArgumentParser

from autoxuexiplaywright.utils.config import get_runtime_config


def main():
    # entrance
    chdir(split(realpath(__file__))[0])
    runtime_config = get_runtime_config()
    parser = ArgumentParser()
    parser.add_argument(
        "--gui", "-g", help="If enable GUI mode.", default=False, type=bool)
    args = parser.parse_args()
    if args.gui:
        runtime_config.update({"gui": True})
    if runtime_config.get("gui", True):
        from autoxuexiplaywright.gui.api import start
        start(argv, **runtime_config)
    else:
        from autoxuexiplaywright.utils.misc import init_logger, start_backend
        init_logger(**runtime_config)
        start_backend(**runtime_config)


if __name__ == "__main__":
    main()  # python -m autoxuexiplaywright
