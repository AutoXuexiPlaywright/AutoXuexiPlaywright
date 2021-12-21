import os
import sys
import queue
import imghdr
import logging
import platform
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtCore import QFile, QMutex, QPoint, QPointF, QSettings, QThread, QWaitCondition, Qt, Signal, QObject, QIODeviceBase
from PySide6.QtWidgets import QApplication, QCheckBox, QVBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QHBoxLayout, QWidget
from AutoXuexiPlaywrightCore import AutoXuexiPlaywrightCore, APPID, APPICONBYTES

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
        super().__init__(flags=Qt.WindowType.FramelessWindowHint)
        icon=QPixmap()
        icon.loadFromData(APPICONBYTES)
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
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        central_widget=QWidget(self)
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        layout=QVBoxLayout()
        title_layout=QHBoxLayout()
        title=QLabel(APPID)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setParent(central_widget)
        title.setObjectName("title")
        score=QLabel("全部得分:0\n今日得分:0")
        score.setAlignment(Qt.AlignmentFlag.AlignVCenter)
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
        ontop_check.setTristate(False)
        ontop_check.setChecked(bool(self.settings.value(APPID+"/ontop",0)))
        control.addWidget(ontop_check)
        control.addWidget(min_btn)
        control.addWidget(close_btn)
        control.setAlignment(Qt.AlignCenter)
        log_panel=QPlainTextEdit()
        log_panel.setParent(central_widget)
        log_panel.setToolTip("当前状态：就绪")
        log_panel.setObjectName("logpanel")
        log_panel.setReadOnly(True)
        log_panel.verticalScrollBar().setObjectName("logpanelscroll")
        start_btn=QPushButton("开始")
        start_btn.setParent(central_widget)
        start_btn.setToolTip("开始")
        start_btn.setObjectName("start")
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
        title_layout.addWidget(score,1)
        title_layout.addWidget(title,8)
        title_layout.addLayout(control,1)
        layout.addLayout(title_layout)
        layout.addWidget(log_panel)
        layout.addWidget(start_btn)
        qss=QFile("MainUI.qss")
        qss.open(QIODeviceBase.OpenModeFlag.ReadOnly)
        self.setStyleSheet(qss.read(qss.size()).data().decode())
        qss.close()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_widget.setLayout(layout)
    def handle_qr(self,qr:bytes):
        label=self.centralWidget().findChild(QLabel,"qrlabel")
        if label is not None and isinstance(label,QLabel):
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
        text,status=QInputDialog.getText(self,"手动输入答案，使用 # 连接多选题的答案:",title,QLineEdit.EchoMode.Normal,"")
        if status==False:
            answer=[""]
        else:
            answer=text.strip().split("#")
        self.answer_queue.put(answer)
        self.wait.wakeAll()
        # TODO: pause QThread and wait for input
    def switch_ontop(self,state:Qt.CheckState):
        if state==Qt.CheckState.Checked:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
            self.settings.setValue(APPID+"/ontop",1)
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
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
if __name__=="__main__":
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    # 将工作目录转移到脚本所在目录，保证下面的相对路径都能正确找到文件
    app=QApplication(sys.argv)
    main_window=MainUI()
    main_window.show()
    sys.exit(app.exec())
    