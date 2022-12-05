from pytest import mark
from playwright.async_api import async_playwright

from autoxuexiplaywright.core.asyncprocessor.handle import emulate_answer
from autoxuexiplaywright.core.asyncprocessor.login import login
from autoxuexiplaywright.utils.storage import get_cache_path


@mark.asyncio
async def test_question_async(times=1, devtools=True):
    cookie = get_cache_path("cookies.json")
    async with async_playwright() as p:
        b = await p.firefox.launch(devtools=devtools)
        context = await b.new_context(storage_state=cookie)
        await login(await context.new_page())
        page = await context.new_page()
        for _ in range(times):
            await page.goto("https://pc.xuexi.cn/points/exam-practice.html")
            await emulate_answer(page)
        await context.close()
