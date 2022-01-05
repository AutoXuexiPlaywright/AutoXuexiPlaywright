import io
import os
import re
import json
import time
import qrcode
import random
import base64
import shutil
import logging
import sqlite3
import requests
import platform
from PIL import Image
from pyzbar import pyzbar
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError
# async in development
import asyncio
from aiohttp import ClientSession
from playwright.async_api import async_playwright, BrowserContext as AsyncBrowserContext, Page as AsyncPage, TimeoutError as AsyncTimeoutError

APPID="AutoXuexiPlaywright"

class XuexiProcessor():
    def __init__(self,gui:bool=False,st:logging.Handler=None,**kwargs):
        default_conf=generate_conf()
        self.is_login=False
        self.gui=gui
        self.job_finish_signal=kwargs["job_finish_signal"] if "job_finish_signal" in kwargs.keys() else None
        self.update_status_signal=kwargs["update_status_signal"] if "update_status_signal" in kwargs.keys() else None
        self.pause_thread_signal=kwargs["pause_thread_signal"] if "pause_thread_signal" in kwargs.keys() else None
        self.answer_queue=kwargs["answer_queue"] if "answer_queue" in kwargs.keys() else None
        self.wait=kwargs["wait"] if "wait" in kwargs.keys() else None
        self.mutex=kwargs["mutex"]if "mutex" in kwargs.keys() else None
        self.qr_control_signal=kwargs["qr_control_signal"] if "qr_control_signal" in kwargs.keys() else None
        self.update_score_signal=kwargs["update_score_signal"] if "update_score_signal" in kwargs.keys() else None
        self.read_urls=set()
        if os.path.exists("config.json")==False:
            with open(file="config.json",mode="w",encoding="utf-8") as writer:
                json.dump(obj=default_conf,fp=writer,ensure_ascii=False,sort_keys=True,indent=4)
        with open(file="config.json",mode="r",encoding="utf-8") as reader:
            self.conf=json.load(reader)
        if self.conf["debug"]==False:
            level=logging.INFO
        else:
            level=logging.DEBUG
            os.putenv("DEBUG","pw:api")
        self.logger=logging.getLogger(__name__)
        fh=logging.FileHandler(filename=APPID+".log",mode="w",encoding="utf-8")
        fmt=logging.Formatter(fmt="%(asctime)s-%(levelname)s-%(message)s",datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(fmt)
        fh.setLevel(level)
        if self.gui==False or st is None:
            st=logging.StreamHandler()
        st.setLevel(level)
        st.setFormatter(fmt)
        self.logger.addHandler(st)
        self.logger.setLevel(level)
        self.logger.addHandler(fh)
        self.update_conf(new_conf=default_conf)
        self.db=sqlite3.connect("data.db")
        self.db.execute("CREATE TABLE IF NOT EXISTS 'history' ('URL' TEXT NOT NULL UNIQUE,'TIME' REAL NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS 'answer' ('QUESTION' TEXT NOT NULL UNIQUE,'ANSWER' TEXT NOT NULL)")
        self.db.commit()
        self.upgrade_db()
        self.logger.info("处理类完成初始化")
    async def start_async(self,test:bool=False):
        if self.conf["async"]==True:
            async with async_playwright() as p:
                if self.conf["browser"]=="chromium":
                    browser=await p.chromium.launch(channel=self.conf["channel"],headless=not self.conf["debug"],proxy=self.conf["proxy"],devtools=self.conf["debug"])
                elif self.conf["browser"]=="firefox":
                    browser=await p.firefox.launch(headless=not self.conf["debug"],proxy=self.conf["proxy"],devtools=self.conf["debug"])
                elif self.conf["browser"]=="webkit":
                    browser=await p.webkit.launch(headless=not self.conf["debug"],proxy=self.conf["proxy"],devtools=self.conf["debug"])
                else:
                    self.logger.error("浏览器类型有误")
                    raise ValueError("设置的浏览器类型有误")
                if os.path.exists("cookies.json"):
                    self.logger.info("已找到 cookie 信息，我们将加载这个信息到上下文实例以进行免登录操作")
                    context=await browser.new_context(storage_state="cookies.json")
                else:
                    self.logger.warning("未找到 cookie 信息，将启动干净的上下文实例")
                    context=await browser.new_context()
                context.set_default_timeout(self.conf["advanced"]["wait_page_secs"]*1000)
                try:
                    await self.login_async(context)
                    if test:
                        await self.test_async(context)
                    else:
                        await self.process_async(context)
                except Exception as e:
                    self.logger.error("处理过程出现错误\n%s" %e)
                    if self.gui==True and self.job_finish_signal is not None:
                        try:
                            self.job_finish_signal.emit()
                        except Exception as e:
                            self.logger.error("提交中止信号出错，GUI 线程可能无法正常中止")
                finally:
                    await context.storage_state(path="cookies.json")
                    self.logger.debug("已保存 cookie 用于尝试下次免登录")
                    await browser.close()
        else:
            self.start(test=test)
        with open("config.json","w",encoding="utf-8") as writer:
            json.dump(obj=self.conf,fp=writer,sort_keys=True,indent=4,ensure_ascii=False)
            self.logger.debug("已更新配置文件")
    def start(self,test:bool=False):
        if self.conf["async"]==False:
            with sync_playwright() as p:
                if self.conf["browser"]=="chromium":
                    browser=p.chromium.launch(channel=self.conf["channel"],headless=not self.conf["debug"],proxy=self.conf["proxy"],devtools=self.conf["debug"])
                elif self.conf["browser"]=="firefox":
                    browser=p.firefox.launch(headless=not self.conf["debug"],proxy=self.conf["proxy"],devtools=self.conf["debug"])
                elif self.conf["browser"]=="webkit":
                    browser=p.webkit.launch(headless=not self.conf["debug"],proxy=self.conf["proxy"],devtools=self.conf["debug"])
                else:
                    self.logger.error("浏览器类型有误")
                    raise ValueError("设置的浏览器类型有误")
                if os.path.exists("cookies.json"):
                    self.logger.info("已找到 cookie 信息，我们将加载这个信息到上下文实例以进行免登录操作")
                    context=browser.new_context(storage_state="cookies.json")
                else:
                    self.logger.warning("未找到 cookie 信息，将启动干净的上下文实例")
                    context=browser.new_context()
                context.set_default_timeout(self.conf["advanced"]["wait_page_secs"]*1000)
                try:
                    self.login(context=context)
                    if test==False:
                        self.process(context=context)
                    else:
                        self.test(context=context)
                except Exception as e:
                    self.logger.error("处理过程出现错误\n%s" %e)
                    if self.gui==True and self.job_finish_signal is not None:
                        try:
                            self.job_finish_signal.emit()
                        except Exception as e:
                            self.logger.error("提交中止信号出错，GUI 线程可能无法正常中止")
                finally:
                    context.storage_state(path="cookies.json")
                    self.logger.debug("已保存 cookie 用于尝试下次免登录")
                    browser.close()
        else:
            asyncio.run(self.start_async(test=test))
        with open("config.json","w",encoding="utf-8") as writer:
            json.dump(obj=self.conf,fp=writer,sort_keys=True,indent=4,ensure_ascii=False)
            self.logger.debug("已更新配置文件")
        self.db.close()
        self.logger.debug("已关闭数据库连接")
        if self.conf["debug"]==False:
            self.logger.info("正在删除临时文件")
            if os.path.exists("video.mp4"):
                os.remove("video.mp4")
            if os.path.exists("qr.png"):
                os.remove("qr.png")
        if self.gui==True and self.job_finish_signal is not None:
            try:
                self.job_finish_signal.emit()
            except Exception as e:
                self.logger.error("提交中止信号出错，GUI 线程可能无法正常中止")
    def update_conf(self,new_conf:dict,old_conf:dict=None,write:bool=True):
        need_update=False
        conf=self.conf if old_conf is None else old_conf
        for key in new_conf.keys():
            self.logger.debug("正在比较键值 %s" %key)
            if key in conf.keys():
                self.logger.debug("配置键 %s 已存在" %key)
                if isinstance(conf[key],dict)==True and isinstance(new_conf[key],dict)==True:
                    self.logger.debug("正在进行递归比较")
                    need_update=self.update_conf(new_conf=new_conf[key],old_conf=conf[key],write=False)
            else:
                self.logger.debug("正在为旧配置添加新配置键 %s" %key)
                conf[key]=new_conf[key]
                need_update=True
        if need_update==True and write==True:
            self.logger.debug("更新后的配置:%s" %old_conf)
            self.logger.info("旧版配置已备份为 config.json.bak")
            shutil.copy("config.json","config.json.bak")
            self.logger.debug("正在更新配置文件")
            with open(file="config.json",mode="w",encoding="utf-8") as writer:
                json.dump(obj=old_conf,fp=writer,ensure_ascii=False,sort_keys=True,indent=4)
        return need_update
    async def login_async(self,context:AsyncBrowserContext):
        self.logger.info("正在开始登录")
        if self.gui==True and self.update_status_signal is not None:
            self.update_status_signal.emit("当前状态:正在登录")
        page=await context.new_page()
        await page.bring_to_front()
        await page.goto("https://pc.xuexi.cn/points/login.html")
        if page.locator("div.main-box").count()==0:
            self.logger.info("未能使用 cookie 免登录，将使用传统方案")
            fnum=0
            while True:
                qglogin=page.locator("div#qglogin")
                try:
                    await qglogin.scroll_into_view_if_needed()
                except AsyncTimeoutError:
                    self.logger.error("加载图片失败")
                    raise RuntimeError("加载二维码图片失败，请检查网络连接并等一会儿再试。")
                locator=qglogin.frame_locator("iframe").locator("div#app img")
                img=base64.b64decode(str(locator.get_attribute("src")).split(",")[1])
                with open(file="qr.png",mode="wb") as writer:
                    writer.write(img)
                self.logger.info("登录二维码已保存至程序文件夹，请扫描下方或者文件夹内的二维码完成登录")
                self.img2shell(img)
                locator=page.locator('div.point-manage')
                try:
                    await locator.wait_for(timeout=300000)
                except AsyncTimeoutError as e:
                    if fnum>self.conf["advanced"]["login_retry"]:
                        self.logger.error("超时次数超过 %d 次，终止尝试" %self.conf["advanced"]["login_retry"])
                        raise e
                    else:
                        fnum=fnum+1
                        await page.reload()
                else:
                    break
        else:
            self.logger.info("成功使用 cookie 免登录")
        await page.close()
        self.logger.info("完成登录")
        self.is_login=True
        if self.gui==True and self.qr_control_signal is not None:
            self.qr_control_signal.emit("".encode())
    def login(self,context:BrowserContext):
        self.logger.info("正在开始登录")
        if self.gui==True and self.update_status_signal is not None:
            self.update_status_signal.emit("当前状态:正在登录")
        page=context.new_page()
        page.bring_to_front()
        page.goto("https://pc.xuexi.cn/points/login.html")
        if page.locator("div.main-box").count()==0:
            self.logger.info("未能使用 cookie 免登录，将使用传统方案")
            fnum=0
            while True:
                qglogin=page.locator("div#qglogin")
                try:
                    qglogin.scroll_into_view_if_needed()
                except TimeoutError:
                    self.logger.error("加载图片失败")
                    raise RuntimeError("加载二维码图片失败，请检查网络连接并等一会儿再试。")
                locator=qglogin.frame_locator("iframe").locator("div#app img")
                img=base64.b64decode(str(locator.get_attribute("src")).split(",")[1])
                with open(file="qr.png",mode="wb") as writer:
                    writer.write(img)
                self.logger.info("登录二维码已保存至程序文件夹，请扫描下方或者文件夹内的二维码完成登录")
                self.img2shell(img)
                locator=page.locator('div.point-manage')
                try:
                    locator.wait_for(timeout=300000)
                except TimeoutError as e:
                    if fnum>self.conf["advanced"]["login_retry"]:
                        self.logger.error("超时次数超过 %d 次，终止尝试" %self.conf["advanced"]["login_retry"])
                        raise e
                    else:
                        fnum=fnum+1
                        page.reload()
                else:
                    break
        else:
            self.logger.info("成功使用 cookie 免登录")
        page.close()
        self.logger.info("完成登录")
        self.is_login=True
        if self.gui==True and self.qr_control_signal is not None:
            self.qr_control_signal.emit("".encode())
    async def process_async(self,context:AsyncBrowserContext):
        if self.is_login==False:
            raise RuntimeError("当前未登录")
        start_time=time.time()
        self.logger.debug("正在获取得分情况")
        page=await context.new_page()
        finished=set()
        today=-1
        total=-1
        while True:
            await page.goto("https://pc.xuexi.cn/points/my-points.html")
            await page.locator('span[class*="my-points-red"]').wait_for()
            locator=page.locator("span.my-points-points")
            points=[point.strip() for point in await locator.all_inner_texts()]
            self.logger.debug("获取总分信息:%s" %points)
            try:
                total=int(points[0])
                today=int(points[1])
            except ValueError:
                self.logger.warning("获取分数信息失败")
            self.logger.info("已获得分数:%d，今日获得分数:%d" %(total,today))
            if self.gui==True and (self.update_score_signal is not None):
                self.update_score_signal.emit((total,today))
            points_content=page.locator("div.my-points-content")
            try:
                await points_content.wait_for()
            except AsyncTimeoutError:
                self.logger.error("未获取到正确的卡片")
                raise RuntimeError("获取分数卡片失败")
            else:                
                cards=points_content.locator("div.my-points-card")
                titles=cards.locator("p.my-points-card-title")
                texts=cards.locator("div.my-points-card-text")
                buttons=cards.locator("div.big")
            self.logger.debug("得分卡片:%s" %[title.strip() for title in await titles.all_inner_texts()])
            finish=True
            for i in range(await cards.count()):
                point_text=(await texts.all_inner_texts())[i].strip()
                have=int(point_text.split("/")[0].replace("分",""))
                target=int(point_text.split("/")[1].replace("分",""))
                card_title=(await titles.all_inner_texts())[i].strip()
                if "视听学习" in card_title:
                    handle_type="video"
                elif "答题" in card_title:
                    handle_type="test"
                else:
                    handle_type="news"
                if have>=target or card_title in finished:
                    self.logger.info("%s 已完成" %card_title)
                    finished.add(card_title)
                else:
                    finish=False
                    self.logger.info("正在处理 %s" %card_title)
                    if self.gui==True and self.update_status_signal is not None:
                        self.update_status_signal.emit("当前状态:正在处理 %s" %card_title)
                    if handle_type!="test":
                        try:
                            async with context.expect_page(timeout=self.conf["advanced"]["wait_newpage_secs"]*1000) as page_info:
                                await buttons.nth(i).click()
                            all_available=self.handle_async(page=(await page_info.value),handle_type=handle_type)
                        except AsyncTimeoutError:
                            all_available=self.handle_async(page=page,handle_type=handle_type)
                        else:
                            if len(context.pages)>1:
                                for page_ in context.pages[1:]:
                                    await page_.close()
                    else:
                        await page.add_init_script("() => delete window.navigator.serviceWorker")
                        await buttons.nth(i).click()
                        all_available=self.handle_async(page=page,handle_type=handle_type)
                        if all_available==False:
                            finished.add(card_title)
                            self.logger.warning("有未完成的任务，但找不到完成它的途径（比如已完成全部专项答题，而每天专项答题的得分项目都会刷新）")
                    break
            if finish==True:
                break
        for page_ in context.pages:
            await page_.close()
        mins,secs=divmod(time.time()-start_time,60)
        hrs,mins=divmod(mins,60)
        self.logger.info("结束所有任务，共计用时 {:0>2d}:{:0>2d}:{:0>2d}".format(int(hrs),int(mins),int(secs)))
    def process(self,context:BrowserContext):
        if self.is_login==False:
            raise RuntimeError("当前未登录")
        start_time=time.time()
        self.logger.debug("正在获取得分情况")
        page=context.new_page()
        finished=set()
        today=-1
        total=-1
        while True:
            page.goto("https://pc.xuexi.cn/points/my-points.html")
            page.locator('span[class*="my-points-red"]').wait_for()
            locator=page.locator("span.my-points-points")
            points=[point.strip() for point in locator.all_inner_texts()]
            self.logger.debug("获取总分信息:%s" %points)
            try:
                total=int(points[0])
                today=int(points[1])
            except ValueError:
                self.logger.warning("获取分数信息失败")
            self.logger.info("已获得分数:%d，今日获得分数:%d" %(total,today))
            if self.gui==True and (self.update_score_signal is not None):
                self.update_score_signal.emit((total,today))
            points_content=page.locator("div.my-points-content")
            try:
                points_content.wait_for()
            except TimeoutError:
                self.logger.error("未获取到正确的卡片")
                raise RuntimeError("获取分数卡片失败")
            else:                
                cards=points_content.locator("div.my-points-card")
                titles=cards.locator("p.my-points-card-title")
                texts=cards.locator("div.my-points-card-text")
                buttons=cards.locator("div.big")
            self.logger.debug("得分卡片:%s" %[title.strip() for title in titles.all_inner_texts()])
            finish=True
            for i in range(cards.count()):
                point_text=texts.all_inner_texts()[i].strip()
                have=int(point_text.split("/")[0].replace("分",""))
                target=int(point_text.split("/")[1].replace("分",""))
                card_title=titles.all_inner_texts()[i].strip()
                if "视听学习" in card_title:
                    handle_type="video"
                elif "答题" in card_title:
                    handle_type="test"
                else:
                    handle_type="news"
                if have>=target or card_title in finished:
                    self.logger.info("%s 已完成" %card_title)
                    finished.add(card_title)
                else:
                    finish=False
                    self.logger.info("正在处理 %s" %card_title)
                    if self.gui==True and self.update_status_signal is not None:
                        self.update_status_signal.emit("当前状态:正在处理 %s" %card_title)
                    if handle_type!="test":
                        try:
                            with context.expect_page(timeout=self.conf["advanced"]["wait_newpage_secs"]*1000) as page_info:
                                buttons.nth(i).click()
                            all_available=self.handle(page=page_info.value,handle_type=handle_type)
                        except TimeoutError:
                            all_available=self.handle(page=page,handle_type=handle_type)
                        else:
                            if len(context.pages)>1:
                                for page_ in context.pages[1:]:
                                    page_.close()
                    else:
                        page.add_init_script("() => delete window.navigator.serviceWorker")
                        buttons.nth(i).click()
                        all_available=self.handle(page=page,handle_type=handle_type)
                        if all_available==False:
                            finished.add(card_title)
                            self.logger.warning("有未完成的任务，但找不到完成它的途径（比如已完成全部专项答题，而每天专项答题的得分项目都会刷新）")
                    break
            if finish==True:
                break
        for page_ in context.pages:
            page_.close()
        mins,secs=divmod(time.time()-start_time,60)
        hrs,mins=divmod(mins,60)
        self.logger.info("结束所有任务，共计用时 {:0>2d}:{:0>2d}:{:0>2d}".format(int(hrs),int(mins),int(secs)))
    async def handle_async(self,page:AsyncPage,handle_type:str):
        self.logger.debug("页面URL:%s" %page.url)
        record_url=""
        available=True
        if handle_type!="test":
            self.logger.debug("非答题模式")
            if handle_type=="video":
                self.logger.debug("处理类型:视频")
                # 视频
                async with page.context.expect_page() as page_info:
                    await page.click('div[data-data-id="tv-station-header"] span.moreText')
                self.logger.debug("已点击“打开”按钮")
                page_2=await page_info.value
                await page_2.bring_to_front()
                async with page_2.context.expect_page() as page_info:
                    await page_2.click('div.more-wrap>p.text')
                self.logger.debug("已点击“片库”按钮")
                page_3=await page_info.value
                await page_3.bring_to_front()
                await page_3.locator('section[data-component-wrapper="22af"]').wait_for()
                while True:
                    divs=page_3.locator('div.textWrapper')
                    if divs.count==0:
                        self.logger.error("未找到有效的视频")
                        raise RuntimeError("未找到有效视频")
                    self.logger.debug("找到 %d 个视频" %divs.count())
                    empty=True
                    page_num=1
                    for i in range(await divs.count()):
                        target_url=await divs.nth(i).get_attribute("data-link-target")
                        target_url="" if target_url is None else target_url
                        target_title=(await divs.nth(i).inner_text()).strip().replace("\n"," ")
                        self.logger.info("正在检查 %s 的阅读记录" %target_title)
                        if self.is_read(target_url)==True:
                            self.logger.info("%s 在 %d 天内已阅读" %(target_title,self.conf["keep_in_database"]))
                            continue
                        async with page_3.context.expect_page() as page_info:
                            await divs.nth(i).click()
                        page_4=await page_info.value
                        try:
                            title=page_4.locator("div.videoSet-article-title")
                            await title.wait_for(timeout=10000)
                        except AsyncTimeoutError:
                            title=page_4.locator("div.video-article-title")
                            await title.wait_for(timeout=10000)
                        self.logger.info("正在处理:%s" %(await title.inner_text()).replace("\n"," "))
                        video=page_4.locator("video")
                        if page_4.url.startswith("https://www.xuexi.cn/lgpage/detail/index.html?id=")==False:
                            self.logger.debug("非正常视频页面")
                            continue
                        start_time=time.time()
                        while True:
                            if time.time()-start_time>=self.conf["advanced"]["read_time"]+random.randint(-5,5):
                                self.logger.debug("达到预计时间，正在结束视频的学习")
                                record_url=page_4.url
                                empty=False
                                break
                            time.sleep(random.uniform(0.0,5.0))
                            await video.scroll_into_view_if_needed()
                            if random.randint(0,1)==1:
                                await page_4.hover('div.videoSet-article-video')
                                try:
                                    await page_4.click('div[class*="prism-play-btn"]',timeout=2000)
                                except AsyncTimeoutError:
                                    try:
                                        await page_4.click('div.outter',timeout=2000)
                                    except AsyncTimeoutError:
                                        self.logger.debug("切换视频播放状态失败")
                            ps=page_4.locator("div.video-article-summary>p,div.videoSet-article-summary>p")
                            if await ps.count()>0:
                                for i in range(await ps.count()):
                                    if ps.nth(i).is_visible()==True:
                                        time.sleep(random.uniform(0.1,5.0))
                                        await ps.nth(i).scroll_into_view_if_needed()
                                time.sleep(random.uniform(0,3))
                                p_r=ps.nth(random.randint(0,await ps.count()-1))
                                if p_r.is_visible()==True:
                                    await p_r.scroll_into_view_if_needed()
                        await page_4.close()
                        break
                    if empty==True:
                        page_num=page_num+1
                        self.logger.warning("没有足够的视频，将尝试在第 %d 页寻找新的视频" %page_num)
                        await page_3.locator('//div/div[contains(text(),">>")]').click()
                    else:
                        break
            elif handle_type=="news":
                self.logger.debug("处理类型:文章")
                # 文章
                async with page.context.expect_page() as page_info:
                    await page.locator('section[data-data-id="zhaiyao-title"] span.moreUrl').click()
                self.logger.debug("已点击“更多头条”链接")
                page_2=await page_info.value
                while True:
                    await page_2.locator("div.text>span").wait_for()
                    spans=page_2.locator('div.text-wrap>span.text')
                    empty=True
                    page_num=1
                    for i in range(await spans.count()):
                        async with page_2.context.expect_page() as page_info:
                            await spans.nth(i).click()
                        self.logger.debug("已点击对应链接")
                        page_3=await page_info.value
                        target_title=(await page_3.locator("div.render-detail-title").inner_text()).strip().replace("\n"," ")
                        self.logger.info("正在处理:%s" %target_title)
                        if page_3.url.startswith("https://www.xuexi.cn/lgpage/detail/index.html?id=")==False:
                            self.logger.debug("非正常文章页面")
                            continue
                        if self.is_read(url=page_3.url)==True:
                            self.logger.info("%s 在 %d 天内已阅读" %(target_title,self.conf["keep_in_database"]))
                            await page_3.close()
                            continue
                        start_time=time.time()
                        while True:
                            if time.time()-start_time>=self.conf["advanced"]["read_time"]+random.randint(-5,5):
                                self.logger.debug("达到预计时间，正在结束文章的学习")
                                record_url=page_3.url
                                empty=False
                                break
                            time.sleep(random.uniform(0.0,5.0))
                            ps=page_3.locator('div[class*="render-detail-content"]>p')
                            if await ps.count()>0:
                                for i in range(await ps.count()):
                                    if ps.nth(i).is_visible()==True:
                                        time.sleep(random.uniform(0.1,5.0))
                                        await ps.nth(i).scroll_into_view_if_needed()
                                time.sleep(random.uniform(0.5,5.0))
                                p_r=ps.nth(random.randint(0,await ps.count()-1))
                                if p_r.is_visible()==True:
                                    await p_r.scroll_into_view_if_needed()
                        await page_3.close()
                        break
                    if empty==True:
                        page_num=page_num+1
                        self.logger.warning("没有足够的文章，将尝试在第 %d 页寻找新的文章" %page_num)
                        await page_2.locator('//div/div[contains(text(),">>")]').click()
                    else:
                        break
            self.record_history(record_url=record_url)
        else:
            self.logger.debug("答题模式")
            page_title=(await page.title()).strip()
            if page_title=="每日答题" or page.url=="https://pc.xuexi.cn/points/exam-practice.html":
                self.logger.debug("正在处理每日答题")
                await self.finish_test_async(page=page)

            elif page_title=="每周答题" or page.url=="https://pc.xuexi.cn/points/exam-weekly-list.html":
                self.logger.debug("正在处理每周答题")
                p=1
                while True:
                    wavailable=False
                    container=page.locator("div.ant-spin-container")
                    await container.wait_for()
                    weeks=container.locator("div.week")
                    self.logger.debug("本页共 %d 个测试" %weeks.count())
                    for i in range(await weeks.count()):
                        test_title=(await weeks.nth(i).locator("div.week-title").inner_text()).strip().replace("\n","")
                        test_stat=await weeks.nth(i).locator("div.stats>span.stat>div").get_attribute("class")
                        test_stat="" if test_stat is None else test_stat
                        btn=weeks.nth(i).locator("button")
                        if "done" in test_stat:
                            self.logger.debug("答题 %s 已完成，正在跳至下一个" %test_title)
                        else:
                            await btn.click()
                            self.logger.info("正在处理:%s" %test_title)
                            await self.finish_test_async(page=page)
                            wavailable=True
                            break
                    if wavailable==True:
                        self.logger.info("已完成测试")
                        break
                    else:
                        next_btn=page.locator('li.ant-pagination-next')
                        p+=1
                        self.logger.warning("本页测试均完成，将在第 %d 页寻找新的未完成测试" %p)
                        await next_btn.click()
                        if next_btn.get_attribute("aria-disabled")=="true":
                            self.logger.warning("无可用测试")
                            break
            elif page_title=="专项答题列表" or page.url=="https://pc.xuexi.cn/points/exam-paper-list.html":
                self.logger.debug("正在处理专项答题")
                p=1
                while True:
                    item=page.locator('div.items')
                    await item.wait_for()
                    items=item.locator('div.item')
                    savailable=False
                    self.logger.debug("本页找到 %d 个测试" %items.count())
                    for i in range(await items.count()):
                        if items.nth(i).locator("a.solution").count()!=0 or items.nth(i).locator("span.points").count()!=0:
                            self.logger.debug("答题已完成，正在跳过")
                        else:
                            test_title=(await items.nth(i).locator('div[class*="item-title"]').inner_text()).replace("...\n","").strip()
                            await items.nth(i).locator('button[type="button"]').click()
                            self.logger.info("正在处理:%s" %test_title)
                            await self.finish_test_async(page=page)
                            savailable=True
                            break
                    if savailable==True:
                        self.logger.info("已完成测试")
                        break
                    else:
                        next_btn=page.locator('li.ant-pagination-next')
                        p+=1
                        self.logger.warning("本页测试均完成，将在第 %d 页寻找新的未完成测试" %p)
                        await next_btn.click()
                        if next_btn.get_attribute("aria-disabled")=="true":
                            self.logger.warning("无可用测试")
                            break
            else:
                self.logger.error("未知的答题内容:%s" %page_title)
        if len(page.context.pages)>=1:
            for page_ in page.context.pages[1:]:
                await page_.close()
        return available
    def handle(self,page:Page,handle_type:str):
        self.logger.debug("页面URL:%s" %page.url)
        record_url=""
        available=True
        if handle_type!="test":
            self.logger.debug("非答题模式")
            if handle_type=="video":
                self.logger.debug("处理类型:视频")
                # 视频
                with page.context.expect_page() as page_info:
                    page.click('div[data-data-id="tv-station-header"] span.moreText')
                self.logger.debug("已点击“打开”按钮")
                page_2=page_info.value
                page_2.bring_to_front()
                with page_2.context.expect_page() as page_info:
                    page_2.click('div.more-wrap>p.text')
                self.logger.debug("已点击“片库”按钮")
                page_3=page_info.value
                page_3.bring_to_front()
                page_3.locator('section[data-component-wrapper="22af"]').wait_for()
                while True:
                    divs=page_3.locator('div.textWrapper')
                    if divs.count==0:
                        self.logger.error("未找到有效的视频")
                        raise RuntimeError("未找到有效视频")
                    self.logger.debug("找到 %d 个视频" %divs.count())
                    empty=True
                    page_num=1
                    for i in range(divs.count()):
                        target_url=divs.nth(i).get_attribute("data-link-target")
                        target_url="" if target_url is None else target_url
                        target_title=divs.nth(i).inner_text().strip().replace("\n"," ")
                        self.logger.info("正在检查 %s 的阅读记录" %target_title)
                        if self.is_read(target_url)==True:
                            self.logger.info("%s 在 %d 天内已阅读" %(target_title,self.conf["keep_in_database"]))
                            continue
                        with page_3.context.expect_page() as page_info:
                            divs.nth(i).click()
                        page_4=page_info.value
                        try:
                            title=page_4.locator("div.videoSet-article-title")
                            title.wait_for(timeout=10000)
                        except TimeoutError:
                            title=page_4.locator("div.video-article-title")
                            title.wait_for(timeout=10000)
                        self.logger.info("正在处理:%s" %title.inner_text().replace("\n"," "))
                        video=page_4.locator("video")
                        if page_4.url.startswith("https://www.xuexi.cn/lgpage/detail/index.html?id=")==False:
                            self.logger.debug("非正常视频页面")
                            continue
                        start_time=time.time()
                        while True:
                            if time.time()-start_time>=self.conf["advanced"]["read_time"]+random.randint(-5,5):
                                self.logger.debug("达到预计时间，正在结束视频的学习")
                                record_url=page_4.url
                                empty=False
                                break
                            time.sleep(random.uniform(0.0,5.0))
                            video.scroll_into_view_if_needed()
                            if random.randint(0,1)==1:
                                page_4.hover('div.videoSet-article-video')
                                try:
                                    page_4.click('div[class*="prism-play-btn"]',timeout=2000)
                                except TimeoutError:
                                    try:
                                        page_4.click('div.outter',timeout=2000)
                                    except TimeoutError:
                                        self.logger.debug("切换视频播放状态失败")
                            ps=page_4.locator("div.video-article-summary>p,div.videoSet-article-summary>p")
                            if ps.count()>0:
                                for i in range(ps.count()):
                                    if ps.nth(i).is_visible()==True:
                                        time.sleep(random.uniform(0.1,5.0))
                                        ps.nth(i).scroll_into_view_if_needed()
                                time.sleep(random.uniform(0,3))
                                p_r=ps.nth(random.randint(0,ps.count()-1))
                                if p_r.is_visible()==True:
                                    p_r.scroll_into_view_if_needed()
                        page_4.close()
                        break
                    if empty==True:
                        page_num=page_num+1
                        self.logger.warning("没有足够的视频，将尝试在第 %d 页寻找新的视频" %page_num)
                        page_3.locator('//div/div[contains(text(),">>")]').click()
                    else:
                        break
            elif handle_type=="news":
                self.logger.debug("处理类型:文章")
                # 文章
                with page.context.expect_page() as page_info:
                    page.locator('section[data-data-id="zhaiyao-title"] span.moreUrl').click()
                self.logger.debug("已点击“更多头条”链接")
                page_2=page_info.value
                while True:
                    page_2.locator("div.text>span").wait_for()
                    spans=page_2.locator('div.text-wrap>span.text')
                    empty=True
                    page_num=1
                    for i in range(spans.count()):
                        with page_2.context.expect_page() as page_info:
                            spans.nth(i).click()
                        self.logger.debug("已点击对应链接")
                        page_3=page_info.value
                        target_title=page_3.locator("div.render-detail-title").inner_text().strip().replace("\n"," ")
                        self.logger.info("正在处理:%s" %target_title)
                        if page_3.url.startswith("https://www.xuexi.cn/lgpage/detail/index.html?id=")==False:
                            self.logger.debug("非正常文章页面")
                            continue
                        if self.is_read(url=page_3.url)==True:
                            self.logger.info("%s 在 %d 天内已阅读" %(target_title,self.conf["keep_in_database"]))
                            page_3.close()
                            continue
                        start_time=time.time()
                        while True:
                            if time.time()-start_time>=self.conf["advanced"]["read_time"]+random.randint(-5,5):
                                self.logger.debug("达到预计时间，正在结束文章的学习")
                                record_url=page_3.url
                                empty=False
                                break
                            time.sleep(random.uniform(0.0,5.0))
                            ps=page_3.locator('div[class*="render-detail-content"]>p')
                            if ps.count()>0:
                                for i in range(ps.count()):
                                    if ps.nth(i).is_visible()==True:
                                        time.sleep(random.uniform(0.1,5.0))
                                        ps.nth(i).scroll_into_view_if_needed()
                                time.sleep(random.uniform(0.5,5.0))
                                p_r=ps.nth(random.randint(0,ps.count()-1))
                                if p_r.is_visible()==True:
                                    p_r.scroll_into_view_if_needed()
                        page_3.close()
                        break
                    if empty==True:
                        page_num=page_num+1
                        self.logger.warning("没有足够的文章，将尝试在第 %d 页寻找新的文章" %page_num)
                        page_2.locator('//div/div[contains(text(),">>")]').click()
                    else:
                        break
            self.record_history(record_url=record_url)
        else:
            self.logger.debug("答题模式")
            page_title=page.title().strip()
            if page_title=="每日答题" or page.url=="https://pc.xuexi.cn/points/exam-practice.html":
                self.logger.debug("正在处理每日答题")
                self.finish_test(page=page)

            elif page_title=="每周答题" or page.url=="https://pc.xuexi.cn/points/exam-weekly-list.html":
                self.logger.debug("正在处理每周答题")
                p=1
                while True:
                    wavailable=False
                    container=page.locator("div.ant-spin-container")
                    container.wait_for()
                    weeks=container.locator("div.week")
                    self.logger.debug("本页共 %d 个测试" %weeks.count())
                    for i in range(weeks.count()):
                        test_title=weeks.nth(i).locator("div.week-title").inner_text().strip().replace("\n","")
                        test_stat=weeks.nth(i).locator("div.stats>span.stat>div").get_attribute("class")
                        test_stat="" if test_stat is None else test_stat
                        btn=weeks.nth(i).locator("button")
                        if "done" in test_stat:
                            self.logger.debug("答题 %s 已完成，正在跳至下一个" %test_title)
                        else:
                            btn.click()
                            self.logger.info("正在处理:%s" %test_title)
                            self.finish_test(page=page)
                            wavailable=True
                            break
                    if wavailable==True:
                        self.logger.info("已完成测试")
                        break
                    else:
                        next_btn=page.locator('li.ant-pagination-next')
                        p+=1
                        self.logger.warning("本页测试均完成，将在第 %d 页寻找新的未完成测试" %p)
                        next_btn.click()
                        if next_btn.get_attribute("aria-disabled")=="true":
                            self.logger.warning("无可用测试")
                            break
            elif page_title=="专项答题列表" or page.url=="https://pc.xuexi.cn/points/exam-paper-list.html":
                self.logger.debug("正在处理专项答题")
                p=1
                while True:
                    item=page.locator('div.items')
                    item.wait_for()
                    items=item.locator('div.item')
                    savailable=False
                    self.logger.debug("本页找到 %d 个测试" %items.count())
                    for i in range(items.count()):
                        if items.nth(i).locator("a.solution").count()!=0 or items.nth(i).locator("span.points").count()!=0:
                            self.logger.debug("答题已完成，正在跳过")
                        else:
                            test_title=items.nth(i).locator('div[class*="item-title"]').inner_text().replace("...\n","").strip()
                            items.nth(i).locator('button[type="button"]').click()
                            self.logger.info("正在处理:%s" %test_title)
                            self.finish_test(page=page)
                            savailable=True
                            break
                    if savailable==True:
                        self.logger.info("已完成测试")
                        break
                    else:
                        next_btn=page.locator('li.ant-pagination-next')
                        p+=1
                        self.logger.warning("本页测试均完成，将在第 %d 页寻找新的未完成测试" %p)
                        next_btn.click()
                        if next_btn.get_attribute("aria-disabled")=="true":
                            self.logger.warning("无可用测试")
                            break
            else:
                self.logger.error("未知的答题内容:%s" %page_title)
        if len(page.context.pages)>=1:
            for page_ in page.context.pages[1:]:
                page_.close()
        return available
    async def finish_test_async(self,page:AsyncPage):
        while True:
            if page.locator('div[class*="ant-modal-wrap"]').count()!=0:
                self.logger.error("答题次数超过网页版限制")
                break
            manual=False
            self.logger.debug("正在寻找问题元素")
            question=page.locator('div.detail-body>div.question')
            await question.scroll_into_view_if_needed()
            title=(await question.locator("div.q-body").inner_text()).strip().replace("\n"," ")
            self.logger.debug("已找到标题:%s" %title)
            answer_in_db=self.get_answer(title=title)
            if answer_in_db!=[]:
                tips=answer_in_db
            else:
                tips_btn=question.locator('span.tips')
                class_value=tips_btn.get_attribute("class")
                if "ant-popover-open" not in "" if class_value is None else class_value:
                    await tips_btn.click()
                    self.logger.debug("已打开提示")
                popover=page.locator('div[class*="ant-popover-placement-bottom"]')
                class_of_popover=await popover.get_attribute("class")
                class_of_popover="" if class_of_popover is None else class_of_popover
                if "ant-popover-hidden" not in class_of_popover:
                    line_feed=popover.locator("div.line-feed")
                    tips=[tip.strip() for tip in await line_feed.locator('font[color="red"]').all_inner_texts()]
                else:
                    tips=[]
                tips_btn=question.locator('span[class*="tips"]')
                class_value=tips_btn.get_attribute("class")
                if "ant-popover-open" in "" if class_value is None else class_value:
                    await tips_btn.click()
                    self.logger.debug("已关闭提示")
                tips=[tip for tip in tips if tip.strip()!='']
                self.logger.debug("已删除提示中的空白字符串")
            self.logger.debug("找到答案:%s" %tips)
            if tips==[]:
                # 手动输入答案
                self.logger.warning("无法找到答案")
                if self.gui==False:
                    tips=input("多个答案请用 # 连接，请输入 %s 的答案:" %title).strip().split("#")
                else:
                    if self.mutex is not None and self.wait is not None:
                        self.mutex.lock()
                        self.wait.wait(self.mutex)
                    else:
                        self.logger.warning("互斥锁或者等待情况为空，子线程可能无法正常暂停")
                    if self.pause_thread_signal is not None:
                        self.pause_thread_signal.emit(title)
                    else:
                        self.logger.warning("暂停信号为空，子线程可能无法正常暂停")
                    if self.answer_queue is not None:
                        tips=self.answer_queue.get()
                    else:
                        tips=[""]
                    if self.mutex is not None:
                        self.mutex.unlock()
                manual=True
                c=asyncio.to_thread(self.get_video_async,page)
            answers_e=question.locator("div.q-answers")
            if answers_e.count()==0:
                answers=question.locator("input.blank")
                blank=True
                self.logger.debug("问题类型为填空题")
            else:
                answers=answers_e.locator('div[class*="q-answer"]')
                blank=False
                self.logger.debug("问题类型为选择题")
            available=False
            if len(tips)==answers.count() and blank==False:
                for i in range(await answers.count()):
                    class_of_answer=answers.nth(i).get_attribute("class")
                    if "chosen" not in "" if class_of_answer is None else class_of_answer:
                        await answers.nth(i).click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                available=True
            else:
                for tip_ in tips:
                    for i in range(await answers.count()):
                        if blank==False:
                            class_of_answer=await answers.nth(i).get_attribute("class")
                            self.logger.debug("获取答案class:%s" %class_of_answer)
                            if class_of_answer is None:
                                self.logger.debug("不正常的选择项目？")
                                continue
                            if "chosen" not in class_of_answer and tip_ in (await answers.nth(i).inner_text()).strip():
                                await answers.nth(i).click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                                self.logger.debug("选择 %s" %(await answers.nth(i).inner_text()).strip())
                                available=True
                        elif i==tips.index(tip_):
                            time.sleep(random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"]))
                            await answers.nth(i).fill(tip_)
                            self.logger.debug("填入 %s" %tip_)
                            available=True
            if available==False:
                self.logger.error("无显式答案")
                r=answers.nth(random.randint(0,await answers.count()))
                if "chosen" not in str(r.get_attribute("class")) and blank==False:
                    await r.click()
                    self.logger.info("随机选择:%s" %(await r.inner_text()).strip())
            while True:
                action_row=page.locator("div.action-row")
                btn_next=action_row.locator('button[class*="next-btn"]')
                if btn_next.is_enabled()==False:
                    self.logger.debug("已点击“提交”按钮")
                    await action_row.locator('button[class*="submit-btn"]').click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                else:
                    self.logger.debug("已点击“下一个”按钮")
                    await btn_next.click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                solution=page.locator('div.solution')
                if solution.count()!=0:
                    if answer_in_db !=[]:
                        self.logger.info("数据库似乎记录了错误的答案？我们将删除这条记录")
                        self.remove_answer(title)
                    self.logger.info("本次答题输入的答案有误，将记录网页的答案")
                    true_answer=[ele.strip() for ele in await solution.locator('font[color="red"]').all_inner_texts()]
                    self.logger.debug("网页获取的原始答案:%s" %true_answer)
                    if true_answer!=[]:
                        if len(true_answer)>await answers.count():
                            part=int(len(true_answer)/await answers.count())
                            true_answer=[" ".join(true_answer[i:i+part]) for i in range(0,len(true_answer),part)]
                        else:
                            self.logger.warning("查询到的答案数不大于需要回答内容数，我们将不记录这个答案")
                            true_answer=[]
                        if blank==True:
                            true_answer=[ans.replace(" ","") for ans in true_answer]
                        self.logger.debug("记录到的真实答案:%s" %true_answer)
                        #self.record_answer(title,true_answer)
                        # TODO: How to get valid answer because tips may not same to answer
                    else:
                        self.logger.warning("从网页上查询真实答案出错")
                else:
                    break
            if manual==True:
                self.record_answer(title=title,answer=tips)
            try:
                container=page.locator('div.ant-spin-nested-loading>div.ant-spin-container')
                await container.wait_for(timeout=self.conf["advanced"]["wait_result_secs"]*1000)
            except AsyncTimeoutError:
                self.logger.debug("无答题结果元素，测试未结束")
            else:
                if container.locator('div.practice-result').count()!=0:
                    self.logger.info("已完成测试")
                    break
                else:
                    self.logger.debug("未完成测试，继续")
    def finish_test(self,page:Page):
        while True:
            if page.locator('div[class*="ant-modal-wrap"]').count()!=0:
                self.logger.error("答题次数超过网页版限制")
                break
            manual=False
            self.logger.debug("正在寻找问题元素")
            question=page.locator('div.detail-body>div.question')
            question.scroll_into_view_if_needed()
            title=question.locator("div.q-body").inner_text().strip().replace("\n"," ")
            self.logger.debug("已找到标题:%s" %title)
            answer_in_db=self.get_answer(title=title)
            if answer_in_db!=[]:
                tips=answer_in_db
            else:
                tips_btn=question.locator('span.tips')
                class_value=tips_btn.get_attribute("class")
                if "ant-popover-open" not in "" if class_value is None else class_value:
                    tips_btn.click()
                    self.logger.debug("已打开提示")
                popover=page.locator('div[class*="ant-popover-placement-bottom"]')
                class_of_popover=popover.get_attribute("class")
                class_of_popover="" if class_of_popover is None else class_of_popover
                if "ant-popover-hidden" not in class_of_popover:
                    line_feed=popover.locator("div.line-feed")
                    tips=[tip.strip() for tip in line_feed.locator('font[color="red"]').all_inner_texts()]
                else:
                    tips=[]
                tips_btn=question.locator('span[class*="tips"]')
                class_value=tips_btn.get_attribute("class")
                if "ant-popover-open" in "" if class_value is None else class_value:
                    tips_btn.click()
                    self.logger.debug("已关闭提示")
                tips=[tip for tip in tips if tip.strip()!='']
                self.logger.debug("已删除提示中的空白字符串")
            self.logger.debug("找到答案:%s" %tips)
            if tips==[]:
                # 手动输入答案
                self.logger.warning("无法找到答案")
                if self.gui==False:
                    tips=input("多个答案请用 # 连接，请输入 %s 的答案:" %title).strip().split("#")
                else:
                    if self.mutex is not None and self.wait is not None:
                        self.mutex.lock()
                        self.wait.wait(self.mutex)
                    else:
                        self.logger.warning("互斥锁或者等待情况为空，子线程可能无法正常暂停")
                    if self.pause_thread_signal is not None:
                        self.pause_thread_signal.emit(title)
                    else:
                        self.logger.warning("暂停信号为空，子线程可能无法正常暂停")
                    if self.answer_queue is not None:
                        tips=self.answer_queue.get()
                    else:
                        tips=[""]
                    if self.mutex is not None:
                        self.mutex.unlock()
                manual=True
                self.get_video(page)
            answers_e=question.locator("div.q-answers")
            if answers_e.count()==0:
                answers=question.locator("input.blank")
                blank=True
                self.logger.debug("问题类型为填空题")
            else:
                answers=answers_e.locator('div[class*="q-answer"]')
                blank=False
                self.logger.debug("问题类型为选择题")
            available=False
            if len(tips)==answers.count() and blank==False:
                for i in range(answers.count()):
                    class_of_answer=answers.nth(i).get_attribute("class")
                    if "chosen" not in "" if class_of_answer is None else class_of_answer:
                        answers.nth(i).click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                available=True
            else:
                for tip_ in tips:
                    for i in range(answers.count()):
                        if blank==False:
                            class_of_answer=answers.nth(i).get_attribute("class")
                            self.logger.debug("获取答案class:%s" %class_of_answer)
                            if class_of_answer is None:
                                self.logger.debug("不正常的选择项目？")
                                continue
                            if "chosen" not in class_of_answer and tip_ in answers.nth(i).inner_text().strip():
                                answers.nth(i).click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                                self.logger.debug("选择 %s" %answers.nth(i).inner_text().strip())
                                available=True
                        elif i==tips.index(tip_):
                            time.sleep(random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"]))
                            answers.nth(i).fill(tip_)
                            self.logger.debug("填入 %s" %tip_)
                            available=True
            if available==False:
                self.logger.error("无显式答案")
                r=answers.nth(random.randint(0,answers.count()))
                if "chosen" not in str(r.get_attribute("class")) and blank==False:
                    r.click()
                    self.logger.info("随机选择:%s" %r.inner_text().strip())
            while True:
                action_row=page.locator("div.action-row")
                btn_next=action_row.locator('button[class*="next-btn"]')
                if btn_next.is_enabled()==False:
                    self.logger.debug("已点击“提交”按钮")
                    action_row.locator('button[class*="submit-btn"]').click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                else:
                    self.logger.debug("已点击“下一个”按钮")
                    btn_next.click(delay=random.uniform(self.conf["advanced"]["answer_sleep_min"],self.conf["advanced"]["answer_sleep_max"])*1000)
                solution=page.locator('div.solution')
                if solution.count()!=0:
                    if answer_in_db !=[]:
                        self.logger.info("数据库似乎记录了错误的答案？我们将删除这条记录")
                        self.remove_answer(title)
                    self.logger.info("本次答题输入的答案有误，将记录网页的答案")
                    true_answer=[ele.strip() for ele in solution.locator('font[color="red"]').all_inner_texts()]
                    self.logger.debug("网页获取的原始答案:%s" %true_answer)
                    if true_answer!=[]:
                        if len(true_answer)>answers.count():
                            part=int(len(true_answer)/answers.count())
                            true_answer=[" ".join(true_answer[i:i+part]) for i in range(0,len(true_answer),part)]
                        else:
                            self.logger.warning("查询到的答案数不大于需要回答内容数，我们将不记录这个答案")
                            true_answer=[]
                        if blank==True:
                            true_answer=[ans.replace(" ","") for ans in true_answer]
                        self.logger.debug("记录到的真实答案:%s" %true_answer)
                        #self.record_answer(title,true_answer)
                        # TODO: How to get valid answer because tips may not same to answer
                    else:
                        self.logger.warning("从网页上查询真实答案出错")
                else:
                    break
            if manual==True:
                self.record_answer(title=title,answer=tips)
            try:
                container=page.locator('div.ant-spin-nested-loading>div.ant-spin-container')
                container.wait_for(timeout=self.conf["advanced"]["wait_result_secs"]*1000)
            except TimeoutError:
                self.logger.debug("无答题结果元素，测试未结束")
            else:
                if container.locator('div.practice-result').count()!=0:
                    self.logger.info("已完成测试")
                    break
                else:
                    self.logger.debug("未完成测试，继续")
    def record_history(self,record_url:str):
        if record_url=="":
            self.logger.warning("想记录的URL为空，跳过记录")
        else:
            self.read_urls.add(record_url)
            record_url=base64.b64encode(record_url.encode()).decode()
            self.db.execute("INSERT INTO 'history' (URL,TIME) VALUES (?,?) ON CONFLICT (URL) DO UPDATE SET TIME=excluded.TIME",(record_url,time.time()))
            self.db.commit()
            self.logger.info("已记录学习历史")
    def record_answer(self,title:str,answer:list):
        if answer==[] or title=="":
            self.logger.warning("想记录的答案非法")
        else:
            title=base64.b64encode(title.encode()).decode()
            self.db.execute("INSERT INTO 'answer' (QUESTION,ANSWER) VALUES (?,?) ON CONFLICT (QUESTION) DO UPDATE SET ANSWER=excluded.ANSWER",(title,base64.b64encode("#".join(answer).encode()).decode()))
            self.db.commit()
            self.logger.info("已记录手动查询的答案")
    def is_read(self,url:str):
        result=False
        if url=="":
            self.logger.warning("查询的URL为空")
        elif url in self.read_urls:
            result=True
        else:
            url=base64.b64encode(url.encode()).decode()
            record_time=self.db.execute("SELECT TIME FROM history WHERE URL=?",(url,)).fetchone()
            if record_time is None:
                record_time=(-1,)
            record_time=float(record_time[0])
            self.logger.debug("数据库查询结果:%s" %record_time)
            if record_time!=-1 and time.time()-record_time<self.conf["keep_in_database"]*24*3600:
                result=True
        return result
    def get_answer(self,title:str):
        result=[]
        if title=="":
            self.logger.warning("查询题目的标题为空")
        else:
            title=base64.b64encode(title.encode()).decode()
            res=self.db.execute("SELECT ANSWER FROM answer WHERE QUESTION=?",(title,)).fetchone()
            if res is not None:
                result=base64.b64decode(str(res[0])).decode().split("#")
                self.logger.debug("数据库查询结果:%s" %result)
            else:
                self.logger.debug("数据库中无记录")
        return result
    def remove_answer(self,title:str):
        title=base64.b64encode(title.encode()).decode()
        self.db.execute("DELETE FROM answer where QUESTION=?",(title,))
        self.db.commit()
    def upgrade_db(self):
        if self.conf["updated"]==False:
            self.logger.info("正在更新数据库存储格式") 
            bak=sqlite3.connect("data.db.bak")
            with bak:
                self.db.backup(bak)
            bak.commit()
            bak.close()
            self.logger.info("正在更新答案库")
            for question in self.db.execute("SELECT QUESTION FROM answer"):
                answer=self.db.execute("SELECT ANSWER from answer WHERE QUESTION= ?",(question[0],)).fetchone()
                try:
                    base64.b64decode(str(question[0]))
                    base64.b64decode(str(answer[0]))
                except Exception:
                    self.db.execute("UPDATE answer SET ANSWER= ? WHERE QUESTION= ?",(base64.b64encode(str(answer[0]).encode()).decode(),str(question[0])))
                    self.db.execute("UPDATE answer SET QUESTION= ? WHERE QUESTION= ?",(base64.b64encode(str(question[0]).encode()).decode(),str(question[0])))
                else:
                    self.logger.debug("似乎问题和答案已被编码？")
            self.logger.info("正在更新历史记录")
            for url in self.db.execute("SELECT URL FROM history"):
                try:
                    base64.b64decode(str(url[0]))
                except Exception:
                    self.db.execute("UPDATE history SET URL= ? WHERE URL= ?",(base64.b64encode(str(url[0]).encode()).decode(),str(url[0])))
                else:
                    self.logger.debug("似乎历史 URL 已被编码？")
            self.db.commit()
            self.logger.info("数据库更新完成")
            self.conf["updated"]=True
        self.db.execute("DELETE FROM history WHERE TIME<?",(time.time()-self.conf["keep_in_database"]*24*3600,))
        self.db.commit()
    def img2shell(self,img:bytes):
        if self.gui==False:
            data=pyzbar.decode(Image.open(io.BytesIO(img)))[0]
            qr=qrcode.QRCode()
            qr.add_data(data.data.decode())
            qr.print_tty()
        else:
            self.logger.info("GUI 模式无法输出二维码到终端，请扫描程序文件夹或者弹出的二维码图片")
            if self.qr_control_signal is not None:
                self.qr_control_signal.emit(img)
    async def get_video_async(self,page:AsyncPage):
        video=page.locator("div#videoplayer")
        if await video.count()==1:
            await video.hover()
            try:
                async with page.expect_response(re.compile(r'https://.+.(m3u8|mp4)')) as response:
                    await page.click('div#videoplayer div.outter',timeout=1000)
            except AsyncTimeoutError as e:
                self.logger.error("下载视频失败，原因:%s" %e)
            else:
                value=await response.value
                headers=await value.all_headers()
                self.logger.debug("开始下载 %s MIME类型视频 %s" %(headers["content-type"],value.url))
                if value.url.endswith(".mp4"):
                    with open("video.mp4","wb") as writer:
                        writer.write(await value.body())
                elif value.url.endswith(".m3u8"):
                    text=await value.text()
                    if self.conf["debug"]==True:
                        with open("playlist.m3u8",mode="w",encoding="utf-8") as writer:
                            writer.write(text)
                        self.logger.debug("已保存播放列表文件")
                    url=urlparse(value.url)
                    prefix="%s://%s/" %(url.scheme,url.netloc+"/".join(url.path.split("/")[:-1]))
                    async def get_content(url:str) -> bytes:
                        async with ClientSession() as session:
                            session.headers.update(headers)
                            async with session.get(url) as response:
                                return await response.read()
                    tasks=[]
                    loop=asyncio.get_event_loop()
                    for line in text.split("\n"):
                        if line.startswith("#")==False:
                            tasks.append(asyncio.ensure_future(get_content(prefix+line)))
                    results=loop.run_until_complete(asyncio.gather(*tasks))
                    with open("video.mp4","wb") as writer:
                        writer.write(bytes().join(results))
                else:
                    self.logger.warning("未知的视频模式")
                self.logger.info("已将视频下载至脚本文件夹下的 video.mp4 文件")
        else:
            self.logger.error("找到 %d 个视频元素" %video.count())
    def get_video(self,page:Page):
        video=page.locator("div#videoplayer")
        if video.count()==1:
            video.hover()
            try:
                with page.expect_response(re.compile(r'https://.+.(m3u8|mp4)')) as response:
                    page.click('div#videoplayer div.outter',timeout=1000)
            except TimeoutError as e:
                self.logger.error("下载视频失败，原因:%s" %e)
            else:
                self.logger.debug("开始下载 %s MIME类型视频 %s" %(response.value.all_headers()["content-type"],response.value.url))
                if response.value.url.endswith(".mp4"):
                    with open("video.mp4","wb") as writer:
                        writer.write(response.value.body())
                elif response.value.url.endswith(".m3u8"):
                    text=response.value.text()
                    if self.conf["debug"]==True:
                        with open("playlist.m3u8",mode="w",encoding="utf-8") as writer:
                            writer.write(text)
                        self.logger.debug("已保存播放列表文件")
                    url=urlparse(response.value.url)
                    prefix="%s://%s/" %(url.scheme,url.netloc+"/".join(url.path.split("/")[:-1]))
                    with open("video.mp4","wb") as writer:
                        i=io.BytesIO()
                        for line in text.split("\n"):
                            if line.startswith("#")==False:
                                self.logger.debug("正在下载视频 %s" %line)
                                i.write(requests.get(url=prefix+line,headers=response.value.all_headers()).content)
                                shutil.copyfileobj(i,writer) 
                else:
                    self.logger.warning("未知的视频模式")
                self.logger.info("已将视频下载至脚本文件夹下的 video.mp4 文件")
        else:
            self.logger.error("找到 %d 个视频元素" %video.count())
    async def test_async(self,context:AsyncBrowserContext):
        # 用于开发时测试脚本功能的函数，在 self.start_async(test=True) 时执行，正常使用时无需此函数
        if self.is_login==False:
            raise RuntimeError("当前未登录")
        page=await context.new_page()
        
        # 在这里放置 async 测试内容
        
        await page.close()
    def test(self,context:BrowserContext):
        # 用于开发时测试脚本功能的函数，在 self.start(test=True) 时执行，正常使用时无需此函数
        if self.is_login==False:
            raise RuntimeError("当前未登录")
        page=context.new_page()

        # 在这里放置测试内容
        
        page.close()
def generate_conf():
    default_conf={
        "async":False,
        "updated":True,
        "debug":False,
        "proxy":None,
        "browser":"chromium",
        "channel":"msedge",
        "keep_in_database":3,
        "advanced":{
            "read_time":60,
            "login_retry":5,
            "answer_sleep_min":3.0,
            "answer_sleep_max":1.5,
            "wait_result_secs":2,
            "wait_page_secs":60,
            "wait_newpage_secs":5
        }
    }
    if platform.system()!="Windows":
        default_conf["browser"]="firefox"
        default_conf["channel"]=None
    return default_conf
