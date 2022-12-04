from playwright.sync_api import sync_playwright
from autoxuexiplaywright.core.syncprocessor.handle import emulate_answer
from autoxuexiplaywright.core.syncprocessor.login import login
from autoxuexiplaywright.utils.storage import get_cache_path


def test_question_sync(times=1, devtools=True):
    cookie = get_cache_path("cookies.json")
    with sync_playwright() as p:
        b = p.firefox.launch(devtools=devtools)
        context = b.new_context(storage_state=cookie)
        login(context.new_page())
        page = context.new_page()
        for _ in range(times):
            page.goto("https://pc.xuexi.cn/points/exam-practice.html")
            emulate_answer(page)
        context.close()
