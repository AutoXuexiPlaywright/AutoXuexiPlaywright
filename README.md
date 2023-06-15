# AutoXuexiPlaywright

## What is this?

A script to finish XuexiQiangguo's everyday task automatically.

## Changes since legacy version

This is a completely rewrite, you can see [CHANGELOG.md](./CHANGELOG.md) for more info.

## How to use?

- Prepare Python  
    We need Python 3.11 and above. Because we use `Self` in function signature and `asyncio.TaskGroup` in code, which are only available on 3.11 and later.
- Install Poetry  
    We use `poetry` to manage dependencies. See [here](https://python-poetry.org/docs/) for more info. For Linux users, we strongly recommend using your distribution's package manager to install poetry. For Arch Linux, you can run `# pacman -Sy python-poetry` to achieve that.
- Install dependencies  
    Open a terminal, go to where the repository is, and run `poetry install` to install dependencies. Poetry will create virtual environment automatically. We have set mirror site of pypi in China so it should not spend too much time.
    Note: If you want to download video on test pages to help solving questions, you must also install optional dependency `python-ffmpeg` and its dependencies.
- Install Qt binding  
    This is only needed if you want to use GUI, you can run `poetry install --with=gui` in repository directory to install it.
- Build and install the project  
    Although you can run the program now, it is more convenient to build a wheel package and install the package to system. If you want to run from source, you can skip this step.  
    Open a terminal, go to where the repository is, run `poetry build`, after command finished, you will find package at `dist` folder of repository. `.whl` package can be installed by `pip install` command.
- Install browser  
    Playwright needs the browsers are installed. If you installed the whl package, Playwright's CLI tool `playwright` should also be installed. You can run `playwright install` to install all the browsers needed.  
    If you choose to run from source, you can run `poetry run playwright install` to finish installing browsers.  
    Browsers' installing may meet very slow speed, you can see [here](https://playwright.dev/python/docs/browsers#install-behind-a-firewall-or-a-proxy) for possible solution.
- Run from source without building  
    You may don't want to build the project and want to run from source instead. You should open a terminal, go to where the repository is, run `poetry run autoxuexiplaywright` to start the program. If you are running program from built package, you should skip this step.
- Run from built package  
    If you are running program from built package, you can simply run `autoxuexiplaywright` from terminal.

For Arch Linux users, we provide a [PKGBUILD](./resources/makepkg/autoxuexiplaywright/PKGBUILD) which may be useful for you.

## Notes

1. This tool is under heavy development and may not as stable as other tools. Some features may also don't work as expected. Everyone's pull request to improve this tool is welcome.

2. This tool is designed only finishing tasks listed on [website](https://xuexi.cn), your max score in one day is 35 after using this tool correctly because some tasks are only available on mobile app.

3. This tool is just for researching purpose, we don't be responsible for any result by using this tool.
