from json import dump
from os.path import isfile
from typing import Literal
from PySide6.QtGui import (
    QMouseEvent, QRegularExpressionValidator
)
from PySide6.QtCore import (
    Qt, QPointF, QPoint, QRegularExpression
)
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QWidget, QFileDialog
)
from playwright._impl._api_structures import ProxySettings

from autoxuexiplaywright.defines.ui import (
    ObjNames, PROXY_REGEX, OPACITY, SETTING_BROWSER_ITEMS, SETTING_ITEM_NAMES
)
from autoxuexiplaywright.defines.core import ANSWER_CONNECTOR, LANGS
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.storage import get_config_path
from autoxuexiplaywright.utils.misc import to_str
from autoxuexiplaywright.utils.config import Config


class SettingsWindow(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.config = Config.get_instance()
        self._start_pos = QPointF(0, 0)
        self.setWindowOpacity(OPACITY)
        main_layout = QVBoxLayout()
        self.title = QLabel(
            get_lang(self.config.lang, "ui-config-window-title"), self)
        self.title.setObjectName(ObjNames.SETTINGS_WINDOW_TITLE)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title)
        contents = QVBoxLayout()
        browser = QHBoxLayout()
        self.set_browser_selecotr()
        browser.addWidget(self.browser_title)
        browser.addWidget(self.browser_selector)
        browser.addWidget(self.channel_title)
        browser.addWidget(self.channel_selector)
        contents.addLayout(browser)
        executable_path = QHBoxLayout()
        self.set_executable_input()
        executable_path.addWidget(self.executable_label)
        executable_path.addWidget(self.executable_input)
        executable_path.addWidget(self.executable_btn)
        contents.addLayout(executable_path)
        skipped_items = QHBoxLayout()
        self.set_skipped_items()
        skipped_items.addWidget(self.skipped_items_label)
        skipped_items.addWidget(self.skipped_items_input)
        contents.addLayout(skipped_items)
        extra = QHBoxLayout()
        lang_layout = QHBoxLayout()
        self.set_extra_items()
        lang_layout.addWidget(self.lang_title)
        lang_layout.addWidget(self.lang_selector)
        extra.addWidget(self.async_check)
        extra.addWidget(self.debug_check)
        extra.addWidget(self.gui_check)
        extra.addLayout(lang_layout)
        contents.addLayout(extra)
        proxy = QVBoxLayout()
        self.set_proxy_widgets()
        proxy.addLayout(self.proxy_address)
        authenticate = QHBoxLayout()
        authenticate.addLayout(self.proxy_username)
        authenticate.addLayout(self.proxy_password)
        proxy.addLayout(authenticate)
        proxy.addLayout(self.proxy_bypass)
        contents.addLayout(proxy)
        operate = QHBoxLayout()
        self.set_operate_btns()
        operate.addWidget(self.save_btn, 8)
        operate.addWidget(self.cancel_btn, 2)
        contents.addLayout(operate)
        main_layout.addLayout(contents)
        self.setLayout(main_layout)

    def set_skipped_items(self):
        self.skipped_items_label = QLabel(
            get_lang(self.config.lang, "ui-config-window-skipped-items-label"), self)
        self.skipped_items_input = QLineEdit(self)
        self.skipped_items_input.setToolTip(get_lang(
            self.config.lang, "ui-config-window-skipped-items-tooltip") % ANSWER_CONNECTOR)
        self.skipped_items_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_SKIPPED_ITEMS)
        skipped_items = self.config.skipped
        if skipped_items != []:
            self.skipped_items_input.setText(
                ANSWER_CONNECTOR.join(skipped_items))
        self.skipped_items_input.editingFinished.connect(  # type: ignore
            self.on_skipped_items_input_edit_finished)

    def set_executable_input(self):
        self.executable_label = QLabel(
            get_lang(self.config.lang, "ui-config-window-executable-label"), self)
        self.executable_input = QLineEdit(self)
        self.executable_input.setToolTip(
            get_lang(self.config.lang, "ui-config-window-executable-tooltip"))
        self.executable_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_EXECUTABLE_INPUT)
        self.executable_input.setText(
            to_str(self.config.executable_path))
        self.executable_input.editingFinished.connect(  # type: ignore
            self.on_executable_input_edit_finished)
        self.executable_btn = QPushButton(
            get_lang(self.config.lang, "ui-config-window-executable-browse-text"), self)
        self.executable_btn.setToolTip(
            get_lang(self.config.lang, "ui-config-window-executable-browse-tooltip"))
        self.executable_btn.clicked.connect(  # type: ignore
            self.on_executable_btn_clicked)

    def set_browser_selecotr(self):
        self.browser_title = QLabel(
            get_lang(self.config.lang, "ui-config-window-browser-title"), self)
        self.browser_selector = QComboBox(self)
        self.browser_selector.setToolTip(
            get_lang(self.config.lang, "ui-config-window-browser-selector-tooltip"))
        self.browser_selector.setObjectName(
            ObjNames.SETTINGS_WINDOW_BROWSER_SELECTOR)
        for item in SETTING_BROWSER_ITEMS:
            self.browser_selector.addItem(item.title(), item)
        self.browser_selector.setCurrentIndex(
            SETTING_BROWSER_ITEMS.index(self.config.browser_id))
        self.browser_selector.currentIndexChanged.connect(  # type: ignore
            self.on_browser_selector_changed)
        self.channel_title = QLabel(
            get_lang(self.config.lang, "ui-config-window-channel-title"), self)
        self.channel_selector = QComboBox(self)
        self.channel_selector.setToolTip(
            get_lang(self.config.lang, "ui-config-window-channel-selector-tooltip"))
        self.channel_selector.setObjectName(
            ObjNames.SETTINGS_WINDOW_CHANNEL_SELECTOR)
        for item in SETTING_ITEM_NAMES.keys():
            self.channel_selector.addItem(SETTING_ITEM_NAMES[item], item)
        channel = self.config.channel
        if channel is not None:
            self.channel_selector.setCurrentIndex(
                list(SETTING_ITEM_NAMES.keys()).index(channel))
        self.channel_selector.setEnabled(
            (not bool(self.browser_selector.currentIndex())) or (not (channel is None)))
        self.channel_selector.currentIndexChanged.connect(  # type: ignore
            self.on_channel_selector_changed)

    def set_extra_items(self):
        self.async_check = QCheckBox(
            get_lang(self.config.lang, "ui-config-window-async"), self)
        self.async_check.setToolTip(
            get_lang(self.config.lang, "ui-config-window-async-tooltip"))
        self.async_check.setObjectName(ObjNames.SETTINGS_WINDOW_ASYNC_CHECK)
        self.async_check.setChecked(self.config.async_mode)
        self.async_check.stateChanged.connect(  # type: ignore
            self.on_async_check_changed)
        self.debug_check = QCheckBox(
            get_lang(self.config.lang, "ui-config-window-debug"), self)
        self.debug_check.setToolTip(
            get_lang(self.config.lang, "ui-config-window-debug-tooltip"))
        self.debug_check.setObjectName(ObjNames.SETTINGS_WINDOW_DEBUG_CHECK)
        self.debug_check.setChecked(self.config.debug)
        self.debug_check.stateChanged.connect(  # type: ignore
            self.on_debug_check_changed)
        self.gui_check = QCheckBox(
            get_lang(self.config.lang, "ui-config-window-gui"), self)
        self.gui_check.setToolTip(
            get_lang(self.config.lang, "ui-config-window-gui-tooltip"))
        self.gui_check.setObjectName(ObjNames.SETTINGS_WINDOW_GUI_CHECK)
        self.gui_check.setChecked(self.config.gui)
        self.gui_check.stateChanged.connect(  # type: ignore
            self.on_gui_check_changed)
        self.lang_title = QLabel(
            get_lang(self.config.lang, "ui-config-window-lang-title"), self)
        self.lang_selector = QComboBox(self)
        self.lang_selector.setToolTip(
            get_lang(self.config.lang, "ui-config-window-lang-selector-tooltip"))
        self.lang_selector.setObjectName(ObjNames.SETTINGS_WINDOW_LANG)
        for item in LANGS:
            self.lang_selector.addItem(item, item)
        self.lang_selector.setCurrentIndex(
            LANGS.index(self.config.lang))
        self.lang_selector.currentIndexChanged.connect(  # type: ignore
            self.on_lang_selector_changed)

    def set_proxy_widgets(self):
        def try_set_text(widget: QLineEdit, key: Literal["server", "username", "password", "bypass"]) -> None:
            if self.config.proxy is not None:
                try:
                    widget.setText(to_str(self.config.proxy[key]))
                except:
                    widget.setText("")
            else:
                widget.setText("")
        self.proxy_address = QHBoxLayout()
        self.proxy_address_label = QLabel(
            get_lang(self.config.lang, "ui-config-window-proxy-address"), self)
        self.proxy_address_input = QLineEdit(self)
        self.proxy_address_input.setToolTip(
            get_lang(self.config.lang, "ui-config-window-proxy-address-tooltip"))
        self.proxy_address_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_PROXY_ADDR)
        self.proxy_address_input.setValidator(
            QRegularExpressionValidator(QRegularExpression(PROXY_REGEX)))
        self.proxy_address_input.editingFinished.connect(  # type: ignore
            self.on_proxy_address_edited)
        try_set_text(self.proxy_address_input, "server")
        self.proxy_address.addWidget(self.proxy_address_label)
        self.proxy_address.addWidget(self.proxy_address_input)

        self.proxy_username = QHBoxLayout()
        self.proxy_username_label = QLabel(
            get_lang(self.config.lang, "ui-config-window-proxy-username"), self)
        self.proxy_username_input = QLineEdit(self)
        self.proxy_username_input.setToolTip(
            get_lang(self.config.lang, "ui-config-window-proxy-username-tooltip"))
        self.proxy_username_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_PROXY_USERNAME)
        self.proxy_username_input.editingFinished.connect(  # type: ignore
            self.on_proxy_username_edited)
        try_set_text(self.proxy_username_input, "username")
        self.proxy_username.addWidget(self.proxy_username_label)
        self.proxy_username.addWidget(self.proxy_username_input)

        self.proxy_password = QHBoxLayout()
        self.proxy_password_label = QLabel(
            get_lang(self.config.lang, "ui-config-window-proxy-password"), self)
        self.proxy_password_input = QLineEdit(self)
        self.proxy_password_input.setEchoMode(
            QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.proxy_password_input.setToolTip(
            get_lang(self.config.lang, "ui-config-window-proxy-password-tooltip"))
        self.proxy_password_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_PROXY_PASSWORD)
        self.proxy_password_input.editingFinished.connect(  # type: ignore
            self.on_proxy_password_edited)
        try_set_text(self.proxy_password_input, "password")
        self.proxy_password.addWidget(self.proxy_password_label)
        self.proxy_password.addWidget(self.proxy_password_input)

        self.proxy_bypass = QHBoxLayout()
        self.proxy_bypass_label = QLabel(
            get_lang(self.config.lang, "ui-config-window-proxy-bypass"), self)
        self.proxy_bypass_input = QLineEdit(self)
        self.proxy_bypass_input.setToolTip(
            get_lang(self.config.lang, "ui-config-window-proxy-bypass-tooltip"))
        self.proxy_bypass_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_PROXY_BYPASS)
        self.proxy_bypass_input.editingFinished.connect(  # type: ignore
            self.on_proxy_bypass_edited)
        try_set_text(self.proxy_bypass_input, "bypass")
        self.proxy_bypass.addWidget(self.proxy_bypass_label)
        self.proxy_bypass.addWidget(self.proxy_bypass_input)

    def set_operate_btns(self):
        self.save_btn = QPushButton(
            get_lang(self.config.lang, "ui-config-window-save"), self)
        self.save_btn.setToolTip(
            get_lang(self.config.lang, "ui-config-window-save-tooltip"))
        self.save_btn.setObjectName(ObjNames.SETTINGS_WINDOW_SAVE)
        self.save_btn.clicked.connect(  # type: ignore
            self.on_save_btn_clicked)
        self.cancel_btn = QPushButton(
            get_lang(self.config.lang, "ui-config-window-cancel"), self)
        self.cancel_btn.setObjectName(ObjNames.SETTINGS_WINDOW_CANCEL)
        self.cancel_btn.clicked.connect(self.close)  # type: ignore

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

    def on_browser_selector_changed(self, idx: int):
        self.config.browser_id = self.browser_selector.currentData()
        self.channel_selector.setEnabled(not bool(idx))
        self.on_channel_selector_changed(idx)

    def on_channel_selector_changed(self, idx: int):
        if self.channel_selector.isEnabled():
            self.config.channel = self.channel_selector.currentData()
        else:
            self.config.channel = None

    def on_lang_selector_changed(self, idx: int):
        self.config.lang = LANGS[idx]

    def on_async_check_changed(self, state: Qt.CheckState):
        self.config.async_mode = state == Qt.CheckState.Checked

    def on_debug_check_changed(self, state: Qt.CheckState):
        self.config.debug = state == Qt.CheckState.Checked

    def on_gui_check_changed(self, state: Qt.CheckState):
        self.config.gui = state == Qt.CheckState.Checked

    def on_save_btn_clicked(self):
        with open(get_config_path("config.json"), "w", encoding="utf-8") as writer:
            dump(self.config.__dict__, writer, sort_keys=True, indent=4)
        self.close()

    def on_executable_btn_clicked(self):
        result: tuple[str] = QFileDialog.getOpenFileName(self, get_lang(  # type: ignore
            self.config.lang, "ui-config-window-executable-browse-title"))
        if result[0] != "":
            self.executable_input.setText(result[0])  # type: ignore
            self.config.executable_path = result[0]
        elif self.config.executable_path is not None:
            self.executable_input.setText(result[0])  # type: ignore
            self.config.executable_path = None

    def on_executable_input_edit_finished(self):
        if isfile(self.executable_input.text()):
            self.config.executable_path = self.executable_input.text()
        if self.executable_input.text() == "" and self.config.executable_path is not None:
            self.config.executable_path = None

    def on_skipped_items_input_edit_finished(self):
        input_text = self.skipped_items_input.text()
        input_items = input_text.split(
            ANSWER_CONNECTOR) if input_text != "" else []
        for i in range(len(input_items)):
            input_items[i] = input_items[i].strip()
        self.config.skipped = input_items

    def on_proxy_address_edited(self):
        if self.proxy_address_input.text() != "":
            if self.config.proxy is not None:
                self.config.proxy["server"] = self.proxy_address_input.text()
            else:
                self.config.proxy = ProxySettings(
                    server=self.proxy_address_input.text())

    def on_proxy_username_edited(self):
        if self.config.proxy is not None:
            self.config.proxy["username"] = self.proxy_username_input.text()
        else:
            self.proxy_username_input.clear()

    def on_proxy_password_edited(self):
        if self.config.proxy is not None:
            self.config.proxy["password"] = self.proxy_password_input.text()
        else:
            self.proxy_password_input.clear()

    def on_proxy_bypass_edited(self):
        if self.config.proxy is not None:
            self.config.proxy["bypass"] = self.proxy_bypass_input.text()
        else:
            self.proxy_bypass_input.clear()


__all__ = ["SettingsWindow"]
