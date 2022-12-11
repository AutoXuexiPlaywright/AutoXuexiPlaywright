from queue import Queue
from imghdr import what
from PySide6.QtGui import (QMouseEvent, QPixmap, QIcon)
from PySide6.QtCore import (QFile, QPoint, QPointF, Qt, QSettings, QThread)
from PySide6.QtWidgets import (QCheckBox, QVBoxLayout, QInputDialog, QLabel, QSystemTrayIcon,
                            QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QHBoxLayout, QWidget)

from autoxuexiplaywright.defines.core import APPID, ANSWER_CONNECTOR
from autoxuexiplaywright.defines.ui import ObjNames, UI_ICON, UI_CONF, OPACITY, UI_WIDTH, UI_HEIGHT, NOTIFY_SECS, SPLIT_TITLE_SIZE
from autoxuexiplaywright.defines.events import EventId
from autoxuexiplaywright.gui.settings import SettingsWindow
from autoxuexiplaywright.gui.objects import SubProcess
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.answerutils import is_valid_answer
from autoxuexiplaywright.utils.storage import get_resource_path
from autoxuexiplaywright.utils.eventmanager import find_event_by_id, clean_callbacks
from autoxuexiplaywright.utils.config import Config


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint)
        self.icon = QPixmap()
        self.icon.loadFromData(UI_ICON)
        self.setWindowIcon(QIcon(self.icon))
        self.setWindowTitle(APPID)
        self.setWindowOpacity(OPACITY)
        self.setObjectName(ObjNames.MAIN)
        self.resize(UI_WIDTH, UI_HEIGHT)
        self._start_pos = QPointF(0, 0)
        self.settings = QSettings(UI_CONF, QSettings.Format.IniFormat)
        self.move(
            self.settings.value("UI/x", 0, int),  # type: ignore
            self.settings.value("UI/y", 0, int)  # type: ignore
        )
        if self.settings.value("UI/ontop", False, bool):
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip(APPID)
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName(ObjNames.CENTRAL_WIDGET)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.set_title_layout()
        self.set_log_panel()
        self.set_start_layout()
        self.main_layout.addLayout(self.title_layout)
        self.main_layout.addWidget(self.log_panel)
        self.main_layout.addLayout(self.start_layout)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_thread = QThread()
        self.jobs = SubProcess()
        self.jobs.moveToThread(self.sub_thread)
        self.tray.setVisible(True)
        self.apply_style()
        self.set_signals()
        self.register_callbacks()

    def set_title_layout(self) -> None:
        config = Config.get_instance()
        self.title_layout = QHBoxLayout()
        self.title = QLabel(APPID)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setObjectName(ObjNames.TITLE)
        self.score = QLabel(get_lang(config.lang, "ui-score-text") % (0, 0))
        self.score.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.setObjectName(ObjNames.SCORE)
        self.control = QHBoxLayout()
        self.close_btn = QPushButton("", self.central_widget)
        self.close_btn.setObjectName(ObjNames.CLOSE)
        self.close_btn.setToolTip(
            get_lang(config.lang, "ui-close-btn-tooltip"))
        self.min_btn = QPushButton("", self.central_widget)
        self.min_btn.setObjectName(ObjNames.MINIMIZE)
        self.min_btn.setToolTip(
            get_lang(config.lang, "ui-minimize-btn-tooltip"))
        self.ontop_check = QCheckBox("", self.central_widget)
        self.ontop_check.setObjectName(ObjNames.ONTOP)
        self.ontop_check.setToolTip(
            get_lang(config.lang, "ui-ontop-checkbox-tooltip"))
        self.control.addWidget(self.ontop_check)
        self.control.addWidget(self.min_btn)
        self.control.addWidget(self.close_btn)
        self.control.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_layout.addWidget(self.score, 1)
        self.title_layout.addWidget(self.title, 8)
        self.title_layout.addLayout(self.control, 1)
        self.title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_start_layout(self) -> None:
        config = Config.get_instance()
        self.start_layout = QHBoxLayout()
        self.start_btn = QPushButton(get_lang(
            config.lang, "ui-start-btn-tooltip"), self.central_widget)
        self.start_btn.setObjectName(ObjNames.START)
        self.start_btn.setToolTip(get_lang(
            config.lang, "ui-start-btn-tooltip"))
        self.settings_btn = QPushButton(get_lang(
            config.lang, "ui-settings-btn-tooltip"), self.central_widget)
        self.settings_btn.setObjectName(ObjNames.SETTINGS)
        self.settings_btn.setToolTip(get_lang(
            config.lang, "ui-settings-btn-tooltip"))
        self.start_layout.addWidget(self.start_btn, 8)
        self.start_layout.addWidget(self.settings_btn, 2)

    def set_log_panel(self) -> None:
        self.log_panel = QPlainTextEdit()
        self.log_panel.setObjectName(ObjNames.LOG_PANEL)
        self.log_panel.setToolTip(
            get_lang(Config.get_instance().lang, "ui-logpanel-default-tooltip"))
        self.log_panel.setReadOnly(True)
        self.log_panel.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.log_panel.verticalScrollBar().setObjectName(
            ObjNames.LOG_PANEL_SCROLL)

    def apply_style(self) -> None:
        qss = QFile(get_resource_path("ui.qss"))
        qss.open(QFile.OpenModeFlag.ReadOnly)
        self.setStyleSheet(qss.readAll().data().decode())

    def set_signals(self) -> None:
        self.jobs.job_finished_signal.connect(self.on_job_finished)
        self.sub_thread.started.connect(self.jobs.start)  # type: ignore
        self.sub_thread.finished.connect(  # type: ignore
            self.on_sub_thread_finished)
        self.jobs.update_log_signal.connect(self.log_panel.appendPlainText)
        self.jobs.update_status_signal.connect(self.log_panel.setToolTip)
        self.jobs.pause_thread_signal.connect(self.on_manual_input_required)
        self.jobs.qr_control_signal.connect(self.on_qr_bytes_recived)
        self.jobs.update_score_signal.connect(self.on_score_updated)
        self.close_btn.clicked.connect(self.close)  # type: ignore
        self.min_btn.clicked.connect(self.on_min_btn_clicked)  # type: ignore
        self.ontop_check.stateChanged.connect(  # type: ignore
            self.on_ontop_state_changed)
        self.start_btn.clicked.connect(  # type: ignore
            self.on_start_btn_clicked)
        self.settings_btn.clicked.connect(  # type: ignore
            self.on_settings_btn_clicked)
        self.tray.activated.connect(self.on_tray_activated)  # type: ignore

    def register_callbacks(self):
        clean_callbacks()
        find_event_by_id(EventId.FINISHED).add_callback(
            self.jobs.job_finished_signal.emit)
        find_event_by_id(EventId.STATUS_UPDATED).add_callback(
            self.jobs.update_status_signal.emit)
        find_event_by_id(EventId.QR_UPDATED).add_callback(
            self.jobs.qr_control_signal.emit)
        find_event_by_id(EventId.SCORE_UPDATED).add_callback(
            self.jobs.update_score_signal.emit)
        find_event_by_id(EventId.ANSWER_REQUESTED).add_callback(
            self.jobs.pause)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._start_pos = event.screenPos()
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        delta = QPoint(round(event.screenPos().x()-self._start_pos.x()),
                       round(event.screenPos().y()-self._start_pos.y()))
        self.move(self.x()+delta.x(), self.y()+delta.y())
        self._start_pos = event.screenPos()
        return super().mouseMoveEvent(event)

    def on_manual_input_required(self, obj: tuple[str, Queue[list[str]]]) -> None:
        title: str = obj[0]
        answer_queue: Queue[list[str]] = obj[1]
        head_title = get_lang(
            Config.get_instance().lang, "ui-manual-input-required") % ANSWER_CONNECTOR
        parsed_title = title.split("\n")
        real_title = parsed_title[0]
        real_title = "\n".join([real_title[i:i+SPLIT_TITLE_SIZE]
                               for i in range(0, len(real_title), SPLIT_TITLE_SIZE)])
        tips = "\n".join(parsed_title[1:]) if len(parsed_title) > 1 else ""
        full_title = "\n".join([head_title, real_title, tips])
        text, status = QInputDialog.getText(
            self, head_title, full_title, QLineEdit.EchoMode.Normal, "", Qt.WindowType.FramelessWindowHint)
        if status:
            answer = [answer_str.strip() for answer_str in text.strip().split(
                ANSWER_CONNECTOR) if is_valid_answer(answer_str.strip())]
        else:
            answer = []
        answer_queue.put(answer)
        self.jobs.wait.wakeAll()

    def on_qr_bytes_recived(self, qr: bytes) -> None:
        for label in self.centralWidget().findChildren(QLabel, ObjNames.QR_LABEL):  # type: ignore
            if isinstance(label, QLabel):
                label.close()
        if qr != "".encode() and what(file="", h=qr) is not None:
            label = QLabel(self.centralWidget())
            label.setObjectName(ObjNames.QR_LABEL)
            label.setWindowModality(Qt.WindowModality.WindowModal)
            pixmap = QPixmap()
            pixmap.loadFromData(qr)
            label.setPixmap(pixmap)
            label.resize(pixmap.size())
            label.move(round((self.centralWidget().width()-label.width())/2),
                       round((self.centralWidget().height()-label.height())/2))
            label.show()

    def on_ontop_state_changed(self, state: Qt.CheckState) -> None:
        if state == Qt.CheckState.Checked:
            self.setWindowFlags(self.windowFlags() |
                                Qt.WindowType.WindowStaysOnTopHint)
            self.settings.setValue("UI/ontop", True)
        else:
            self.setWindowFlags(self.windowFlags() | -
                                Qt.WindowType.WindowStaysOnTopHint)
            self.settings.setValue("UI/ontop", False)
        self.show()

    def on_sub_thread_finished(self) -> None:
        config = Config.get_instance()
        self.log_panel.setToolTip(
            get_lang(config.lang, "ui-logpanel-default-tooltip"))
        self.start_btn.setEnabled(True)
        self.start_btn.setToolTip(get_lang(
            config.lang, "ui-start-btn-tooltip"))
        self.start_btn.setText(get_lang(
            config.lang, "ui-start-btn-tooltip"))
        for label in self.centralWidget().findChildren(QLabel, ObjNames.QR_LABEL):  # type: ignore
            if isinstance(label, QLabel):
                label.close()

    def on_score_updated(self, score: tuple[int]):
        if score != (-1, -1):
            self.score.setText(
                get_lang(Config.get_instance().lang, "ui-score-text") % score)

    def close(self) -> bool:
        self.tray.setVisible(False)
        self.settings.setValue("UI/x", self.x())
        self.settings.setValue("UI/y", self.y())
        return super().close()

    def on_start_btn_clicked(self) -> None:
        config = Config.get_instance()
        self.start_btn.setEnabled(False)
        self.start_btn.setToolTip(
            get_lang(config.lang, "ui-start-btn-processing-tooltip"))
        self.start_btn.setText(
            get_lang(config.lang, "ui-start-btn-processing-tooltip"))
        self.sub_thread.start()

    def on_settings_btn_clicked(self):
        setting_window = SettingsWindow(self.central_widget)
        setting_window.setObjectName(ObjNames.SETTINGS_WINDOW)
        setting_window.resize(round(self.width()*3/4),
                              round(self.height()*3/8))
        setting_window.move(self.x()+round((self.width()-setting_window.width())/2),
                            self.y()+round((self.height()-setting_window.height())/2))
        setting_window.exec_()

    def on_min_btn_clicked(self):
        if self.tray.isSystemTrayAvailable():
            self.hide()
            self.tray.setVisible(True)
        else:
            self.showMinimized()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.setHidden(not self.isHidden())

    def on_job_finished(self, finish_str: str):
        self.tray.showMessage(get_lang(Config.get_instance().lang, "ui-tray-notification-title-info"), finish_str,
                              QSystemTrayIcon.MessageIcon.Information, NOTIFY_SECS*1000
                              )

        self.sub_thread.quit()


__all__ = ["MainWindow"]
