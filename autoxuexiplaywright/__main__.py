from os import chdir
from os.path import split, realpath
from sys import argv
from argparse import ArgumentParser, BooleanOptionalAction

from autoxuexiplaywright.utils.config import Config


def main():
    # entrance
    chdir(split(realpath(__file__))[0])
    parser = ArgumentParser()
    parser.add_argument(
        "--gui", "-g",  action=BooleanOptionalAction, help="If enable GUI mode by force.", dest="gui")
    parser.add_argument(
        "--config", "-c", action="store", help="The config file path", dest="config")
    args = parser.parse_args()
    config = Config.get_instance(args.config)
    if isinstance(args.gui, bool):
        config.gui = args.gui
    if config.gui:
        from autoxuexiplaywright.gui.api import start
        start(argv)
    else:
        from autoxuexiplaywright.utils.misc import start
        start()


if __name__ == "__main__":
    main()  # python -m autoxuexiplaywright
