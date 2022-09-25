import os
import sys
import argparse
from autoxuexiplaywright.utils import config, misc


def main():
    # entrance
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    runtime_config = config.get_runtime_config()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gui", "-g", help="If enable GUI mode.", default=False, type=bool)
    args = parser.parse_args()
    if args.gui:
        runtime_config.update({"gui": True})
    if runtime_config.get("gui", True):
        from autoxuexiplaywright.gui import api
        api.start(sys.argv, **runtime_config)
    else:
        misc.init_logger(**runtime_config)
        misc.start_backend(**runtime_config)


if __name__ == "__main__":
    main()  # python -m autoxuexiplaywright
