import json
import queue
import imghdr
import logging
import platform
from PySide6.QtGui import QAction, QContextMenuEvent, QDoubleValidator, QIntValidator, QMouseEvent, QPixmap, QRegularExpressionValidator
from PySide6.QtCore import QFile, QMutex, QPoint, QPointF, QSettings, QThread, QWaitCondition, Qt, Signal, QObject
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QMenu, QTableWidget, QTableWidgetItem, QVBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QHBoxLayout, QWidget
from AutoXuexiPlaywrightCore import AutoXuexiPlaywrightCore, APPID, APPICON, get_bytes

if platform.system()=="Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
    # 让Windows的任务栏图标可以正常显示
class QHandler(logging.Handler):
    def __init__(self, signal) -> None:
        super().__init__()
        self.signal=signal
    def emit(self, record: logging.LogRecord) -> None:
        self.signal.emit(self.format(record))
class SubProcessJob(QObject):
    def __init__(self,answer_queue,job_finish_signal,update_log_signal,update_status_signal,pause_thread_signal,wait:QWaitCondition,
                 mutex:QMutex,qr_control_signal,update_score_signal) -> None:
        super().__init__()
        self.answer_queue=answer_queue
        self.wait=wait
        self.mutex=mutex
        self.job_finish_signal=job_finish_signal
        self.update_log_signal=update_log_signal
        self.update_status_signal=update_status_signal
        self.update_score_signal=update_score_signal
        self.pause_thread_signal=pause_thread_signal
        self.qr_control_signal=qr_control_signal
        self.qhandler=QHandler(update_log_signal)
    def start(self):
        processor=AutoXuexiPlaywrightCore.XuexiProcessor(gui=True,st=self.qhandler,answer_queue=self.answer_queue,
                                                         job_finish_signal=self.job_finish_signal,update_status_signal=self.update_status_signal,
                                                         pause_thread_signal=self.pause_thread_signal,wait=self.wait,mutex=self.mutex,
                                                         qr_control_signal=self.qr_control_signal,update_score_signal=self.update_score_signal)
        processor.start()
class MainUI(QMainWindow):
    job_finish_signal=Signal()
    pause_thread_signal=Signal(str)
    update_log_signal=Signal(str)
    update_status_signal=Signal(str)
    update_score_signal=Signal(tuple)
    qr_control_signal=Signal(bytes)
    def __init__(self) -> None:
        super().__init__(None,Qt.FramelessWindowHint)
        icon=QPixmap()
        icon.loadFromData(get_bytes(APPICON))
        self._start_pos=QPointF(0.0,0.0)
        self.answer_queue=queue.Queue(1)
        self.mutex=QMutex()
        self.wait=QWaitCondition()
        self.settings=QSettings(APPID+"GUI.ini",QSettings.Format.IniFormat,self)
        self.setWindowTitle(APPID)
        self.setWindowIcon(icon)
        self.setWindowOpacity(0.9)
        self.setObjectName("main")
        self.resize(800,600)
        self.move(int(self.settings.value(APPID+"/x",0)),int(self.settings.value(APPID+"/y",0)))
        if bool(int(self.settings.value(APPID+"/ontop",0)))==True:
            self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        central_widget=QWidget(self)
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        layout=QVBoxLayout()
        title_layout=QHBoxLayout()
        title=QLabel(APPID)
        title.setAlignment(Qt.AlignCenter)
        title.setParent(central_widget)
        title.setObjectName("title")
        score=QLabel("全部得分:0\n今日得分:0")
        score.setAlignment(Qt.AlignVCenter)
        score.setParent(central_widget)
        score.setObjectName("score")
        control=QHBoxLayout()
        close_btn=QPushButton()
        close_btn.setParent(central_widget)
        close_btn.setToolTip("关闭")
        close_btn.setObjectName("close")
        min_btn=QPushButton()
        min_btn.setParent(central_widget)
        min_btn.setToolTip("最小化")
        min_btn.setObjectName("minimize")
        ontop_check=QCheckBox()
        ontop_check.setParent(central_widget)
        ontop_check.setToolTip("切换置顶")
        ontop_check.setObjectName("ontop")
        ontop_check.setChecked(bool(self.settings.value(APPID+"/ontop",0)))
        control.addWidget(ontop_check)
        control.addWidget(min_btn)
        control.addWidget(close_btn)
        control.setAlignment(Qt.AlignCenter)
        log_panel=QPlainTextEdit()
        log_panel.setParent(central_widget)
        log_panel.setToolTip("当前状态:就绪")
        log_panel.setObjectName("logpanel")
        log_panel.setReadOnly(True)
        log_panel.verticalScrollBar().setObjectName("logpanelscroll")
        log_panel.setContextMenuPolicy(Qt.NoContextMenu)
        start_layout=QHBoxLayout()
        start_btn=QPushButton("开始")
        start_btn.setParent(central_widget)
        start_btn.setToolTip("开始")
        start_btn.setObjectName("start")
        config_btn=QPushButton("设置")
        config_btn.setToolTip("核心设置")
        config_btn.setObjectName("config")
        self.update_log_signal.connect(log_panel.appendPlainText)
        self.update_status_signal.connect(log_panel.setToolTip)
        self.pause_thread_signal.connect(self.pause_thread)
        self.qr_control_signal.connect(self.handle_qr)
        self.update_score_signal.connect(lambda scores:score.setText("全部得分:%d\n今日得分:%d" %scores))
        self.wthread=QThread()
        self.job=SubProcessJob(answer_queue=self.answer_queue,job_finish_signal=self.job_finish_signal,update_log_signal=self.update_log_signal,
                               update_status_signal=self.update_status_signal,pause_thread_signal=self.pause_thread_signal,wait=self.wait,
                               mutex=self.mutex,qr_control_signal=self.qr_control_signal,
                               update_score_signal=self.update_score_signal)
        self.job.moveToThread(self.wthread)
        self.wthread.started.connect(self.job.start)
        self.wthread.finished.connect(lambda: (log_panel.setToolTip("当前状态:就绪"),start_btn.setEnabled(True),start_btn.setToolTip("开始"),start_btn.setText("开始")))
        self.job_finish_signal.connect(self.wthread.quit)
        close_btn.clicked.connect(self.close)
        min_btn.clicked.connect(self.showMinimized)
        ontop_check.stateChanged.connect(self.switch_ontop)
        start_btn.clicked.connect(lambda:(self.wthread.start(),start_btn.setEnabled(False),start_btn.setToolTip("处理中..."),start_btn.setText("处理中...")))
        config_btn.clicked.connect(lambda:SettingWindow(self).exec())
        title_layout.addWidget(score,1)
        title_layout.addWidget(title,8)
        title_layout.addLayout(control,1)
        start_layout.addWidget(start_btn,8)
        start_layout.addWidget(config_btn,2)
        layout.addLayout(title_layout)
        layout.addWidget(log_panel)
        layout.addLayout(start_layout)
        qss=QFile("MainUI.qss")
        qss.open(QFile.ReadOnly)
        self.setStyleSheet(qss.readAll().data().decode())
        qss.close()
        title_layout.setAlignment(Qt.AlignCenter)
        layout.setAlignment(Qt.AlignCenter)
        central_widget.setLayout(layout)
    def handle_qr(self,qr:bytes):
        for label in self.centralWidget().findChildren(QLabel,"qrlabel"):
            if isinstance(label,QLabel):
                label.close()
        if qr!="".encode() and imghdr.what(file="",h=qr) is not None:
            label=QLabel(self.centralWidget())
            label.setObjectName("qrlabel")
            label.setWindowModality(Qt.WindowModal)
            pixmap=QPixmap()
            pixmap.loadFromData(qr)
            label.setPixmap(pixmap)
            label.resize(pixmap.size())
            label.move(round((self.centralWidget().width()-label.width())/2),round((self.centralWidget().height()-label.height())/2))
            label.show()
    def pause_thread(self,title:str):
        length=15
        parsed_title=title.split("\n")
        real_title=parsed_title[0]
        real_title="\n".join([real_title[i:i+length] for i in range(0,len(real_title),length)])
        if len(parsed_title)>1:
            available_choices=parsed_title[1]
        else:
            available_choices=""
        text,status=QInputDialog.getText(self,"手动输入答案，输入框内的数据可作为参考，使用 # 连接多选题的答案:",real_title,QLineEdit.Normal,available_choices,Qt.FramelessWindowHint)
        if status==False:
            answer=[""]
        else:
            answer=text.strip().split("#")
        self.answer_queue.put(answer)
        self.wait.wakeAll()
    def switch_ontop(self,state:Qt.CheckState):
        if state==Qt.CheckState.Checked:
            self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
            self.settings.setValue(APPID+"/ontop",1)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.settings.setValue(APPID+"/ontop",0)
        self.show()
    def close(self) -> bool:
        self.settings.setValue(APPID+"/x",self.x())
        self.settings.setValue(APPID+"/y",self.y())
        return super().close()
    def mousePressEvent(self, a0: QMouseEvent) -> None:
        self._start_pos=a0.globalPosition()
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        return super().mousePressEvent(a0)
    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().mouseReleaseEvent(a0)
    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        delta=QPoint(round(a0.globalPosition().x()-self._start_pos.x()),round(a0.globalPosition().y()-self._start_pos.y()))
        self.move(self.x()+delta.x(),self.y()+delta.y())
        self._start_pos=a0.globalPosition()
        return super().mouseMoveEvent(a0)
class SettingWindow(QDialog):
    def __init__(self, parent:QWidget) -> None:
        super().__init__(parent=parent,f=Qt.FramelessWindowHint)
        self.setWindowOpacity(0.9)
        self.setObjectName("config_main")
        file=QFile("config.json")
        file.open(QFile.ReadOnly)
        if file.exists():
            self.conf=json.loads(file.readAll().data())
        else:
            self.conf=AutoXuexiPlaywrightCore.generate_conf()
        file.close()
        layout=QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        title=QLabel("设置编辑器",self)
        title.setObjectName("config_title")
        title.setAlignment(Qt.AlignCenter)
        browser=QHBoxLayout()
        browser_title=QLabel("浏览器类型:",self)
        browser_selector=QComboBox(self)
        browser_selector.setToolTip("设置浏览器类型")
        browser_selector.setObjectName("browser")
        items=["chromium","firefox","webkit"]
        for item in items:
            browser_selector.addItem(item.title(),item)
        browser_selector.setCurrentIndex(items.index(self.conf["browser"]))
        channel_title=QLabel("浏览器子类型:",self)
        channel_selector=QComboBox(self)
        channel_selector.setToolTip("设置浏览器子类型，此选项在部分浏览器不可用")
        channel_selector.setObjectName("channel")
        item_names={
            "msedge":"Microsoft Edge","msedge-beta":"Microsoft Edge Beta","msedge-dev":"Microsoft Edge Dev",
            "chrome":"Google Chrome","chrome-beta":"Google Chrome Beta","chrome-dev":"Google Chrome Dev",
            "chromium":"Google Chromium","chromium-beta":"Google Chromium Beta","chromium-dev":"Google Chromium Dev"
        }
        for item in item_names.keys():
            channel_selector.addItem(item_names[item],item)
        if "channel" in self.conf.keys():
            channel_selector.setCurrentIndex(list(item_names.keys()).index(self.conf["channel"]))
        channel_selector.setEnabled(not bool(browser_selector.currentIndex()))
        browser_selector.currentIndexChanged.connect(lambda idx: (self.conf.update({"browser":browser_selector.currentData()}),channel_selector.setEnabled(not bool(idx))))
        channel_selector.currentIndexChanged.connect(lambda idx: self.conf.update({"channel":channel_selector.currentData()}) if channel_selector.isEnabled() else self.conf.update({"channel",None}))        
        browser.addWidget(browser_title)
        browser.addWidget(browser_selector)
        browser.addWidget(channel_title)
        browser.addWidget(channel_selector)
        extra=QHBoxLayout()
        debug=QCheckBox("调试模式",self)
        debug.setToolTip("是否启用调试模式")
        debug.setObjectName("debug")
        debug.setChecked(self.conf["debug"])
        debug.stateChanged.connect(lambda state: self.conf.update({"debug":state==Qt.Checked}))
        extra.addWidget(debug,1)
        async_check=QCheckBox("异步 API")
        async_check.setToolTip("使用 Playwright 的异步 API 完成处理\n注意；此功能正在开发阶段，极度不稳定")
        async_check.setObjectName("async")
        async_check.setChecked(self.conf["async"])
        async_check.stateChanged.connect(lambda state: self.conf.update({"async":state==Qt.Checked}))
        extra.addWidget(async_check)
        keep_in_database=QHBoxLayout()
        keep_in_database_label=QLabel("历史保存天数:",self)
        keep_in_database_input=QLineEdit(self)
        keep_in_database_input.setValidator(QIntValidator(1,30))
        keep_in_database_input.setToolTip("设置数据库中历史记录的保存天数(0-30)")
        keep_in_database_input.setObjectName("keep_in_database")
        keep_in_database_input.textEdited.connect(lambda text: self.conf.update({"keep_in_database":int(text)}))
        keep_in_database_input.setText(str(self.conf["keep_in_database"]))
        keep_in_database.addWidget(keep_in_database_label)
        keep_in_database.addWidget(keep_in_database_input)
        extra.addLayout(keep_in_database,1)
        proxy=QVBoxLayout()
        proxy_label=QLabel("代理列表:",self)
        proxy_list=EnhancedTableWidget(self)
        proxy_list.setObjectName("proxy")
        proxy_list.horizontalHeader().setObjectName("proxy_header")
        proxy_list.verticalHeader().hide()
        proxy_list.setToolTip("所有的代理列表")
        proxy_list.setSelectionBehavior(QTableWidget.SelectRows)
        proxy_list.setEditTriggers(QTableWidget.NoEditTriggers)
        proxy_list.setFocusPolicy(Qt.NoFocus)
        proxy_list.setColumnCount(3)
        proxy_list.setHorizontalHeaderLabels(["服务器","用户名","密码"])
        if self.conf["proxy"] is not None:
            remove_current=QAction("删除",proxy_list)
            remove_current.setObjectName("remove_proxy")
            remove_current.triggered.connect(lambda:proxy_list.remove_row(remove_current))
            proxy_list.menu.addAction(remove_current)
            for proxy_item in self.conf["proxy"]:
                proxy_list.insertRow(proxy_list.rowCount())
                for i in range(3):
                    widget_item=QTableWidgetItem(list(proxy_item.values())[i])
                    proxy_list.setItem(proxy_list.rowCount()-1,i,widget_item)
        proxy.addWidget(proxy_label)
        proxy.addWidget(proxy_list)
        advanced=QVBoxLayout()
        answer_sleep=QHBoxLayout()
        answer_sleep_label=QLabel("答题休眠范围:")
        answer_sleep.addWidget(answer_sleep_label)
        answer_sleep_min=QLineEdit(self)
        answer_sleep_min.setToolTip("最小值(1.0-10.0)")
        answer_sleep_min.setObjectName("answer_sleep_min")
        answer_sleep_min.setValidator(QDoubleValidator(1.0,10.0,1))
        answer_sleep_min.setText(str(self.conf["advanced"]["answer_sleep_min"]))
        answer_sleep_min.textEdited.connect(lambda text: self.conf["advanced"].update({"answer_sleep_min":float(text)}))
        answer_sleep.addWidget(answer_sleep_min)
        answer_sleep_line=QLabel("-")
        answer_sleep.addWidget(answer_sleep_line)
        answer_sleep_max=QLineEdit(self)
        answer_sleep_max.setToolTip("最大值(1.0-10.0)")
        answer_sleep.addWidget(answer_sleep_max)
        answer_sleep_max.setObjectName("answer_sleep_max")
        answer_sleep_max.setValidator(QDoubleValidator(1.0,10.0,1))
        answer_sleep_max.setText(str(self.conf["advanced"]["answer_sleep_max"]))
        answer_sleep_max.textEdited.connect(lambda text: self.conf["advanced"].update({"answer_sleep_max":float(text)}))
        advanced.addLayout(answer_sleep)
        line=QHBoxLayout()
        login_retry=QHBoxLayout()
        login_retry_label=QLabel("登录重试次数:")
        login_retry.addWidget(login_retry_label)
        login_retry_input=QLineEdit(self)
        login_retry_input.setToolTip("登录失败的重试次数(0-10)")
        login_retry_input.setObjectName("login_retry")
        login_retry_input.setValidator(QIntValidator(0,10))
        login_retry_input.setText(str(self.conf["advanced"]["login_retry"]))
        login_retry_input.textEdited.connect(lambda text:self.conf["advanced"].update({"login_retry":int(text)}))
        login_retry.addWidget(login_retry_input)
        line.addLayout(login_retry)
        read_time=QHBoxLayout()
        read_time_label=QLabel("阅读时间:")
        read_time.addWidget(read_time_label)
        read_time_input=QLineEdit()
        read_time_input.setToolTip("阅读时长(秒),(60-300)")
        read_time_input.setObjectName("read_time")
        read_time_input.setValidator(QIntValidator(60,300))
        read_time_input.setText(str(self.conf["advanced"]["read_time"]))
        read_time_input.textEdited.connect(lambda text:self.conf["advanced"].update({"read_time":int(text)}))
        read_time.addWidget(read_time_input)
        line.addLayout(read_time)
        advanced.addLayout(line)
        line2=QHBoxLayout()
        wait_new_page=QHBoxLayout()
        wait_new_page_label=QLabel("等待新标签页超时:")
        wait_new_page.addWidget(wait_new_page_label)
        wait_new_page_input=QLineEdit()
        wait_new_page_input.setToolTip("等待新标签页出现的超时(秒)(1-30)")
        wait_new_page_input.setObjectName("wait_newpage_secs")
        wait_new_page_input.setValidator(QIntValidator(1,30))
        wait_new_page_input.setText(str(self.conf["advanced"]["wait_newpage_secs"]))
        wait_new_page_input.textEdited.connect(lambda text:self.conf["advanced"].update({"wait_newpage_secs":int(text)}))
        wait_new_page.addWidget(wait_new_page_input)
        line2.addLayout(wait_new_page)
        wait_page=QHBoxLayout()
        wait_page_label=QLabel("等待网页加载超时:")
        wait_page.addWidget(wait_page_label)
        wait_page_input=QLineEdit()
        wait_page_input.setToolTip("等待网页加载的最大时间(秒)(10-600)")
        wait_page_input.setObjectName("wait_page_secs")
        wait_page_input.setValidator(QIntValidator(10,600))
        wait_page_input.setText(str(self.conf["advanced"]["wait_page_secs"]))
        wait_page_input.textEdited.connect(lambda text:self.conf["advanced"].update({"wait_page_secs":int(text)}))
        wait_page.addWidget(wait_page_input)
        line2.addLayout(wait_page)
        wait_result=QHBoxLayout()
        wait_result_label=QLabel("等待答题结果超时:")
        wait_result.addWidget(wait_result_label)
        wait_result_input=QLineEdit()
        wait_result_input.setToolTip("等待答题结果元素出现的超时(秒)(1,30)")
        wait_result_input.setObjectName("wait_result_secs")
        wait_result_input.setValidator(QIntValidator(1,30))
        wait_result_input.setText(str(self.conf["advanced"]["wait_result_secs"]))
        wait_result_input.textEdited.connect(lambda text:self.conf["advanced"].update({"wait_result_secs":int(text)}))
        wait_result.addWidget(wait_result_input)
        line2.addLayout(wait_result)
        advanced.addLayout(line2)
        save=QHBoxLayout()
        save_btn=QPushButton("保存")
        save_btn.setToolTip("保存设置，将在下次执行处理时应用")
        save_btn.setObjectName("save")
        save_btn.clicked.connect(self.save_config)
        save.addWidget(save_btn)
        cancel_btn=QPushButton("取消")
        cancel_btn.setToolTip("取消设置")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.close)
        save.addWidget(cancel_btn)
        layout.addWidget(title)
        layout.addLayout(browser)
        layout.addLayout(extra)
        layout.addLayout(proxy)
        layout.addLayout(advanced)
        layout.addLayout(save)
        self.setLayout(layout)
        self.resize(int(parent.width()*3/4),int(parent.height()*3/4))
        self.move(parent.x()+int((parent.width()-self.width())/2),parent.y()+int((parent.height()-self.height())/2))
    def save_config(self):
        with open("config.json","w",encoding="utf-8") as writer:
            json.dump(self.conf,writer,ensure_ascii=False,sort_keys=True,indent=4)
        self.close()
    def update_proxy(self,proxy_list:QTableWidget):
        proxy=[]
        for row in range(proxy_list.rowCount()):
            proxy_dic={}
            for col in range(proxy_list.columnCount()):
                item=proxy_list.item(row,col)
                if item is None:
                    item=proxy_list.cellWidget(row,col)
                if col==0:
                    proxy_dic["server"]=item.text() if isinstance(item,(QLineEdit,QTableWidgetItem)) else None
                elif col==1:
                    proxy_dic["username"]=item.text() if isinstance(item,(QLineEdit,QTableWidgetItem)) else None
                elif col==2:
                    proxy_dic["password"]=item.text() if isinstance(item,(QLineEdit,QTableWidgetItem)) else None
            proxy.append(proxy_dic)
        proxy=None if proxy==[] else proxy
        self.conf.update({"proxy":proxy})
class EnhancedTableWidget(QTableWidget):
    def __init__(self,parent:SettingWindow):
        super().__init__(parent)
        self.menu=QMenu(self)
        add_new=QAction("添加",self.menu)
        add_new.setObjectName("add_proxy")
        add_new.triggered.connect(self.append_row)
        self.menu.addAction(add_new)
    def append_row(self):
        self.insertRow(self.rowCount())
        for i in range(self.columnCount()):
            edit=QLineEdit(self)
            edit.setObjectName("edit")
            edit.setProperty("col",i)
            edit.setProperty("row",self.rowCount()-1)
            if i==0:
                edit.setValidator(QRegularExpressionValidator(r"(https?|socks[45])://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"))
            elif i==self.columnCount()-1:
                edit.editingFinished.connect(self.edit_finished)
            self.setCellWidget(self.rowCount()-1,i,edit)
        if self.findChildren(QAction,"remove_proxy")==[]:
            remove=QAction("删除",self)
            remove.setObjectName("remove_proxy")
            remove.triggered.connect(lambda:self.remove_row(remove))
            self.menu.addAction(remove)
    def edit_finished(self):
        for item in self.findChildren(QLineEdit,"edit"):
            if isinstance(item,QLineEdit):
                col=item.property("col")
                row=item.property("row")
                self.removeCellWidget(row,col)
                self.setItem(row,col,QTableWidgetItem(item.text()))
        self.refresh()
    def remove_row(self,remove:QAction):
        selects=self.selectedItems()
        if len(selects)>0:
            self.removeRow(self.row(selects[0]))
        if self.rowCount()==0 and remove in self.menu.actions():
            self.menu.removeAction(remove) 
        self.refresh()
    def refresh(self):
        for item in self.findChildren(QLineEdit,"edit"):
            if isinstance(item,QLineEdit):
                item.clearFocus()
        parent=self.parentWidget()
        if isinstance(parent,SettingWindow):
            parent.update_proxy(self)
    def contextMenuEvent(self, arg__1:QContextMenuEvent) -> None:
        self.menu.popup(arg__1.globalPos())
        self.menu.exec()
        return super().contextMenuEvent(arg__1)
