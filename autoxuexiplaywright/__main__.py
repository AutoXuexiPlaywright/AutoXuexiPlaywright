import os
import sys
from autoxuexiplaywright.utils import config, misc


def main():
    # entrance
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    runtime_config = config.get_runtime_config()
    if runtime_config.get("gui", True):
        from autoxuexiplaywright.gui import api
        api.start(*sys.argv, **runtime_config)
    else:
        misc.start_backend(*sys.argv, **runtime_config)


if __name__ == "__main__":
    main()  # python -m autoxuexiplaywright
