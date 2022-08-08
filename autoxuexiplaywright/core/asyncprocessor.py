import logging
import asyncio
from autoxuexiplaywright.utils import database, misc, lang
from autoxuexiplaywright.defines import core, urls, selectors
from playwright.async_api import Page, TimeoutError, async_playwright

__all__ = ["start"]


def start(*args, **kwargs) -> None:
    asyncio.run(run(*args, **kwargs))


async def run(*args, **kwargs) -> None:
    misc.init_logger(*args, **kwargs)


async def login(page: Page) -> None:
    await page.goto(urls.LOGIN_PAGE)

