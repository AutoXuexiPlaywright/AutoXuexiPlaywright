import queue
import imghdr
from autoxuexiplaywright.defines import core, ui, events
from autoxuexiplaywright.gui import settings, objects
from autoxuexiplaywright.utils import lang, answerutils, storage, eventmanager
from qtpy.QtGui import (QMouseEvent, QPixmap, QIcon)
from qtpy.QtCore import (QFile, QPoint, QPointF, Qt, QSettings, QThread)
from qtpy.QtWidgets import (QCheckBox, QVBoxLayout, QInputDialog, QLabel, QSystemTrayIcon,
                            QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QHBoxLayout, QWidget)
__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(parent=None, flags=Qt.WindowType.FramelessWindowHint)
        self.icon = QPixmap()
        self.icon.loadFromData(ui.UI_ICON)
        self._start_pos = QPointF(0, 0)
        self.kwargs = kwargs
        self.settings = QSettings(ui.UI_CONF, QSettings.Format.IniFormat)
        self.setWindowIcon(QIcon(self.icon))
        self.setWindowTitle(core.APPID)
        self.setWindowOpacity(ui.OPACITY)
        self.setObjectName(ui.ObjNames.MAIN)
        self.resize(ui.UI_WIDTH, ui.UI_HEIGHT)
        self.move(
            self.settings.value("UI/x", 0, int),
            self.settings.value("UI/y", 0, int)
        )
        if self.settings.value("UI/ontop", False, bool):
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            )
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip(core.APPID)
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName(ui.ObjNames.CENTRAL_WIDGET)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.set_title_layout()
        self.set_log_panel()
        self.set_start_layout()
        self.main_layout.addLayout(self.title_layout)
        self.main_layout.addWidget(self.log_panel)
        self.main_layout.addLayout(self.start_layout)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.sub_thread = QThread()
        self.jobs = objects.SubProcess(**self.kwargs)
        self.jobs.moveToThread(self.sub_thread)
        self.tray.setVisible(True)
        self.apply_style()
        self.set_signals()
        self.register_callbacks()

    def set_title_layout(self) -> None:
        self.title_layout = QHBoxLayout()
        self.title = QLabel(core.APPID)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setObjectName(ui.ObjNames.TITLE)
        self.score = QLabel(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-score-text") % (0, 0))
        self.score.setAlignment(Qt.AlignVCenter)
        self.score.setObjectName(ui.ObjNames.SCORE)
        self.control = QHBoxLayout()
        self.close_btn = QPushButton("", self.central_widget)
        self.close_btn.setObjectName(ui.ObjNames.CLOSE)
        self.close_btn.setToolTip(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-close-btn-tooltip"))
        self.min_btn = QPushButton("", self.central_widget)
        self.min_btn.setObjectName(ui.ObjNames.MINIMIZE)
        self.min_btn.setToolTip(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-minimize-btn-tooltip"))
        self.ontop_check = QCheckBox("", self.central_widget)
        self.ontop_check.setObjectName(ui.ObjNames.ONTOP)
        self.ontop_check.setToolTip(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-ontop-checkbox-tooltip"))
        self.control.addWidget(self.ontop_check)
        self.control.addWidget(self.min_btn)
        self.control.addWidget(self.close_btn)
        self.control.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.score, 1)
        self.title_layout.addWidget(self.title, 8)
        self.title_layout.addLayout(self.control, 1)
        self.title_layout.setAlignment(Qt.AlignCenter)

    def set_start_layout(self) -> None:
        self.start_layout = QHBoxLayout()
        self.start_btn = QPushButton(lang.get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-start-btn-tooltip"), self.central_widget)
        self.start_btn.setObjectName(ui.ObjNames.START)
        self.start_btn.setToolTip(lang.get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-start-btn-tooltip"))
        self.settings_btn = QPushButton(lang.get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-settings-btn-tooltip"), self.central_widget)
        self.settings_btn.setObjectName(ui.ObjNames.SETTINGS)
        self.settings_btn.setToolTip(lang.get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-settings-btn-tooltip"))
        self.start_layout.addWidget(self.start_btn, 8)
        self.start_layout.addWidget(self.settings_btn, 2)

    def set_log_panel(self) -> None:
        self.log_panel = QPlainTextEdit()
        self.log_panel.setObjectName(ui.ObjNames.LOG_PANEL)
        self.log_panel.setToolTip(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-logpanel-default-tooltip"))
        self.log_panel.setReadOnly(True)
        self.log_panel.setContextMenuPolicy(Qt.NoContextMenu)
        self.log_panel.verticalScrollBar().setObjectName(
            ui.ObjNames.LOG_PANEL_SCROLL)

    def apply_style(self) -> None:
        qss = QFile(storage.get_resource_path("ui.qss"))
        qss.open(QFile.ReadOnly)
        self.setStyleSheet(qss.readAll().data().decode())

    def set_signals(self) -> None:
        self.jobs.job_finished_signal.connect(self.on_job_finished)
        self.sub_thread.started.connect(self.jobs.start)
        self.sub_thread.finished.connect(self.on_sub_thread_finished)
        self.jobs.update_log_signal.connect(self.log_panel.appendPlainText)
        self.jobs.update_status_signal.connect(self.log_panel.setToolTip)
        self.jobs.pause_thread_signal.connect(self.on_manual_input_required)
        self.jobs.qr_control_signal.connect(self.on_qr_bytes_recived)
        self.jobs.update_score_signal.connect(self.on_score_updated)
        self.close_btn.clicked.connect(self.close)
        self.min_btn.clicked.connect(self.on_min_btn_clicked)
        self.ontop_check.stateChanged.connect(self.on_ontop_state_changed)
        self.start_btn.clicked.connect(self.on_start_btn_clicked)
        self.settings_btn.clicked.connect(self.on_settings_btn_clicked)
        self.tray.activated.connect(self.on_tray_activated)

    def register_callbacks(self):
        eventmanager.clean_callbacks()
        eventmanager.find_event_by_id(events.EventId.FINISHED).add_callback(
            self.jobs.job_finished_signal.emit)
        eventmanager.find_event_by_id(events.EventId.STATUS_UPDATED).add_callback(
            self.jobs.update_status_signal.emit)
        eventmanager.find_event_by_id(events.EventId.QR_UPDATED).add_callback(
            self.jobs.qr_control_signal.emit)
        eventmanager.find_event_by_id(events.EventId.SCORE_UPDATED).add_callback(
            self.jobs.update_score_signal.emit)
        eventmanager.find_event_by_id(events.EventId.ANSWER_REQUESTED).add_callback(
            self.jobs.pause)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        self._start_pos = a0.screenPos()
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        return super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().mouseReleaseEvent(a0)

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        delta = QPoint(round(a0.screenPos().x()-self._start_pos.x()),
                       round(a0.screenPos().y()-self._start_pos.y()))
        self.move(self.x()+delta.x(), self.y()+delta.y())
        self._start_pos = a0.screenPos()
        return super().mouseMoveEvent(a0)

    def on_manual_input_required(self, obj: tuple) -> None:
        title: str = obj[0]
        answer_queue: queue.Queue = obj[1]
        head_title = lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-manual-input-required") % core.ANSWER_CONNECTOR
        parsed_title = title.split("\n")
        real_title = parsed_title[0]
        real_title = "\n".join([real_title[i:i+ui.SPLIT_TITLE_SIZE]
                               for i in range(0, len(real_title), ui.SPLIT_TITLE_SIZE)])
        tips = "\n".join(parsed_title[1:]) if len(parsed_title) > 1 else ""
        full_title = "\n".join([head_title, real_title, tips])
        text, status = QInputDialog.getText(
            self, head_title, full_title, QLineEdit.Normal, "", Qt.FramelessWindowHint)
        if status:
            answer = [answer_str.strip() for answer_str in text.strip().split(
                core.ANSWER_CONNECTOR) if answerutils.is_valid_answer(answer_str.strip())]
        else:
            answer = []
        answer_queue.put(answer)
        self.jobs.wait.wakeAll()

    def on_qr_bytes_recived(self, qr: bytes) -> None:
        for label in self.centralWidget().findChildren(QLabel, ui.ObjNames.QR_LABEL):
            if isinstance(label, QLabel):
                label.close()
        if qr != "".encode() and imghdr.what(file="", h=qr) is not None:
            label = QLabel(self.centralWidget())
            label.setObjectName(ui.ObjNames.QR_LABEL)
            label.setWindowModality(Qt.WindowModal)
            pixmap = QPixmap()
            pixmap.loadFromData(qr)
            label.setPixmap(pixmap)
            label.resize(pixmap.size())
            label.move(round((self.centralWidget().width()-label.width())/2),
                       round((self.centralWidget().height()-label.height())/2))
            label.show()

    def on_ontop_state_changed(self, state: Qt.CheckState) -> None:
        if state == Qt.CheckState.Checked:
            self.setWindowFlags(Qt.FramelessWindowHint |
                                Qt.WindowStaysOnTopHint)
            self.settings.setValue("UI/ontop", True)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.settings.setValue("UI/ontop", False)
        self.show()

    def on_sub_thread_finished(self) -> None:
        self.log_panel.setToolTip(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-logpanel-default-tooltip"))
        self.start_btn.setEnabled(True)
        self.start_btn.setToolTip(lang.get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-start-btn-tooltip"))
        self.start_btn.setText(lang.get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-start-btn-tooltip"))
        for label in self.centralWidget().findChildren(QLabel, ui.ObjNames.QR_LABEL):
            if isinstance(label, QLabel):
                label.close()

    def on_score_updated(self, score: tuple[int]):
        if score != (-1, -1):
            self.score.setText(lang.get_lang(self.kwargs.get(
                "lang", "zh-cn"), "ui-score-text") % score)

    def close(self) -> None:
        self.tray.setVisible(False)
        self.settings.setValue("UI/x", self.x())
        self.settings.setValue("UI/y", self.y())
        super().close()

    def on_start_btn_clicked(self) -> None:
        self.start_btn.setEnabled(False)
        self.start_btn.setToolTip(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-start-btn-processing-tooltip"))
        self.start_btn.setText(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-start-btn-processing-tooltip"))
        self.sub_thread.start()

    def on_settings_btn_clicked(self):
        setting_window = settings.SettingsWindow(self.central_widget)
        setting_window.setObjectName(ui.ObjNames.SETTINGS_WINDOW)
        setting_window.resize(round(self.width()*3/4),
                              round(self.height()*3/4))
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
        self.tray.showMessage(lang.get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-tray-notification-title-info"), finish_str,
            QSystemTrayIcon.MessageIcon.Information, ui.NOTIFY_SECS*1000
        )

        self.sub_thread.quit()
