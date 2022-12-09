from os import chdir
from os.path import split, realpath
from sys import argv
from argparse import ArgumentParser

from autoxuexiplaywright.utils.config import Config


def main():
    # entrance
    chdir(split(realpath(__file__))[0])
    config=Config.get_instance()
    parser = ArgumentParser()
    parser.add_argument(
        "--gui", "-g", help="If enable GUI mode.", default=False, type=bool)
    args = parser.parse_args()
    if args.gui:
        config.gui=True
    if config.gui:
        from autoxuexiplaywright.gui.api import start
        start(argv)
    else:
        from autoxuexiplaywright.utils.misc import start
        start()


if __name__ == "__main__":
    main()  # python -m autoxuexiplaywright
