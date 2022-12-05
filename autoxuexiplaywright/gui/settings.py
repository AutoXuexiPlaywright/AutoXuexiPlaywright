from json import load, dump
from typing import Union
from os.path import isfile
from qtpy.QtGui import (
    QMouseEvent, QRegularExpressionValidator, QContextMenuEvent
)
from qtpy.QtCore import (
    Qt, QPointF, QPoint, QRegularExpression
)
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QMenu, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QHBoxLayout, QWidget, QFileDialog
)

from autoxuexiplaywright.defines.ui import (
    ObjNames, PROXY_REGEX, OPACITY, SETTING_BROWSER_ITEMS, SETTING_ITEM_NAMES
)
from autoxuexiplaywright.defines.core import ANSWER_CONNECTOR, LANGS
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.storage import get_config_path
from autoxuexiplaywright.utils.misc import to_str


class ProxyTableWidget(QTableWidget):
    def __init__(self, rows: int, parent: QWidget, **kwargs):
        super().__init__(rows, 3, parent)
        self.kwargs = kwargs
        self.menu = QMenu("", self)
        self.menu.addAction(get_lang(
            self.kwargs.get("lang", "zh-cn"), "ui-config-window-add-proxy"), self.add_new_proxy)
        self.setObjectName(ObjNames.SETTINGS_WINDOW_PROXY)
        self.horizontalHeader().setObjectName(ObjNames.SETTINGS_WINDOW_PROXY_HEADER)
        self.verticalHeader().hide()
        self.setToolTip(get_lang(self.kwargs.get(
            "lang", "zh-cn"), "ui-config-window-proxy-list-tooltip"))
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalHeaderLabels([
            get_lang(self.kwargs.get("lang", "zh-cn"),
                     "ui-config-window-proxy-list-headers-0"),
            get_lang(self.kwargs.get("lang", "zh-cn"),
                     "ui-config-window-proxy-list-headers-1"),
            get_lang(self.kwargs.get("lang", "zh-cn"),
                     "ui-config-window-proxy-list-headers-2")
        ])
        proxy = self.kwargs.get("proxy")
        if proxy is not None:
            self.remove_proxy = self.menu.addAction(get_lang(
                self.kwargs.get("lang", "zh-cn"), "ui-config-window-remove-proxy"), self.remove_current_proxy)
            for proxy_item in proxy:
                if isinstance(proxy_item, dict):
                    self.insertRow(self.rowCount())
                    for i in range(3):
                        self.setItem(self.rowCount()-1, i,
                                     QTableWidgetItem(list(proxy_item.values())[i]))
        else:
            self.remove_proxy = None

    def add_new_proxy(self):
        self.insertRow(self.rowCount())
        for i in range(self.columnCount()):
            edit = QLineEdit(self)
            edit.setObjectName(ObjNames.SETTINGS_WINDOW_EDIT)
            edit.setProperty("col", i)
            edit.setProperty("row", self.rowCount()-1)
            if i == 0:
                edit.setValidator(QRegularExpressionValidator(
                    QRegularExpression(PROXY_REGEX)))
            elif i == 2:
                edit.editingFinished.connect(
                    self.on_edit_finished)
            self.setCellWidget(self.rowCount()-1, i, edit)
        if self.remove_proxy is None:
            self.remove_proxy = self.menu.addAction(get_lang(
                self.kwargs.get("lang", "zh-cn"), "ui-config-window-remove-proxy"), self.remove_current_proxy)

    def on_edit_finished(self):
        for item in self.findChildren(QLineEdit, ObjNames.SETTINGS_WINDOW_EDIT):
            if isinstance(item, QLineEdit):
                col = int(item.property("col"))
                row = int(item.property("row"))
                self.removeCellWidget(row, col)
                self.setItem(row, col, QTableWidgetItem(
                    item.text()))
                item.clearFocus()
                item.deleteLater()
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item is None or item.text() == "":
                    self.removeRow(row)
                    break
        self.remove_invalid_rows_and_refresh_data()

    def remove_current_proxy(self):
        selects = self.selectedItems()
        if len(selects) == 3:
            self.removeRow(self.row(selects[0]))
        self.remove_invalid_rows_and_refresh_data()

    def remove_invalid_rows_and_refresh_data(self):
        if self.rowCount() == 0 and self.remove_proxy is not None:
            self.menu.removeAction(self.remove_proxy)
            self.remove_proxy = None
        parent = self.parentWidget()
        if isinstance(parent, SettingsWindow):
            parent.conf.update({"proxy": self.construct_proxy_dict()})

    def construct_proxy_dict(self) -> Union[list, None]:
        proxy = []
        for row in range(self.rowCount()):
            proxy_dic = {}
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if isinstance(item, QTableWidgetItem):
                    text = item.text()
                    if col == 0 and text != "":
                        proxy_dic["server"] = text
                    if col == 1 and text != "":
                        proxy_dic["username"] = text
                    if col == 2 and text != "":
                        proxy_dic["password"] = text
            if proxy_dic != {}:
                proxy.append(proxy_dic)
        if proxy == []:
            proxy = None
        return proxy

    def contextMenuEvent(self, arg__1: QContextMenuEvent) -> None:
        self.menu.popup(arg__1.globalPos())
        self.menu.exec_()
        return super().contextMenuEvent(arg__1)


class SettingsWindow(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self._start_pos = QPointF(0, 0)
        self.setWindowOpacity(OPACITY)
        with open(get_config_path("config.json"), "r", encoding="utf-8") as reader:
            self.conf: dict = load(reader)
        main_layout = QVBoxLayout()
        self.title = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-title"), self)
        self.title.setObjectName(ObjNames.SETTINGS_WINDOW_TITLE)
        self.title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.title)
        browser = QHBoxLayout()
        self.set_browser_selecotr()
        browser.addWidget(self.browser_title)
        browser.addWidget(self.browser_selector)
        browser.addWidget(self.channel_title)
        browser.addWidget(self.channel_selector)
        main_layout.addLayout(browser)
        executable_path = QHBoxLayout()
        self.set_executable_input()
        executable_path.addWidget(self.executable_label)
        executable_path.addWidget(self.executable_input)
        executable_path.addWidget(self.executable_btn)
        main_layout.addLayout(executable_path)
        skipped_items = QHBoxLayout()
        self.set_skipped_items()
        skipped_items.addWidget(self.skipped_items_label)
        skipped_items.addWidget(self.skipped_items_input)
        main_layout.addLayout(skipped_items)
        extra = QHBoxLayout()
        lang_layout = QHBoxLayout()
        self.set_extra_items()
        lang_layout.addWidget(self.lang_title)
        lang_layout.addWidget(self.lang_selector)
        extra.addWidget(self.async_check)
        extra.addWidget(self.debug_check)
        extra.addWidget(self.gui_check)
        extra.addLayout(lang_layout)
        main_layout.addLayout(extra)
        proxy = QVBoxLayout()
        self.set_proxy_widgets()
        proxy.addWidget(self.proxy_label)
        proxy.addWidget(self.proxy_list)
        main_layout.addLayout(proxy)
        operate = QHBoxLayout()
        self.set_operate_btns()
        operate.addWidget(self.save_btn, 8)
        operate.addWidget(self.cancel_btn, 2)
        main_layout.addLayout(operate)
        self.setLayout(main_layout)

    def set_skipped_items(self):
        self.skipped_items_label = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-skipped-items-label"), self)
        self.skipped_items_input = QLineEdit(self)
        self.skipped_items_input.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-skipped-items-tooltip") % ANSWER_CONNECTOR)
        self.skipped_items_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_SKIPPED_ITEMS)
        skipped_items: list = self.conf.get("skipped_items", [])
        if skipped_items != []:
            self.skipped_items_input.setText(
                ANSWER_CONNECTOR.join(skipped_items))
        self.skipped_items_input.editingFinished.connect(
            self.on_skipped_items_input_edit_finished)

    def set_executable_input(self):
        self.executable_label = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-executable-label"), self)
        self.executable_input = QLineEdit(self)
        self.executable_input.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-executable-tooltip"))
        self.executable_input.setObjectName(
            ObjNames.SETTINGS_WINDOW_EXECUTABLE_INPUT)
        self.executable_input.setText(
            to_str(self.conf.get("executable_path")))
        self.executable_input.editingFinished.connect(
            self.on_executable_input_edit_finished)
        self.executable_btn = QPushButton(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-executable-browse-text"), self)
        self.executable_btn.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-executable-browse-tooltip"))
        self.executable_btn.clicked.connect(self.on_executable_btn_clicked)

    def set_browser_selecotr(self):
        self.browser_title = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-browser-title"), self)
        self.browser_selector = QComboBox(self)
        self.browser_selector.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-browser-selector-tooltip"))
        self.browser_selector.setObjectName(
            ObjNames.SETTINGS_WINDOW_BROWSER_SELECTOR)
        for item in SETTING_BROWSER_ITEMS:
            self.browser_selector.addItem(item.title(), item)
        self.browser_selector.setCurrentIndex(
            SETTING_BROWSER_ITEMS.index(self.conf.get("browser", "firefox")))
        self.browser_selector.currentIndexChanged.connect(
            self.on_browser_selector_changed)
        self.channel_title = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-channel-title"), self)
        self.channel_selector = QComboBox(self)
        self.channel_selector.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-channel-selector-tooltip"))
        self.channel_selector.setObjectName(
            ObjNames.SETTINGS_WINDOW_CHANNEL_SELECTOR)
        for item in SETTING_ITEM_NAMES.keys():
            self.channel_selector.addItem(SETTING_ITEM_NAMES[item], item)
        channel = self.conf.get("channel")
        if channel is not None:
            self.channel_selector.setCurrentIndex(
                list(SETTING_ITEM_NAMES.keys()).index(channel))
        self.channel_selector.setEnabled(
            (not bool(self.browser_selector.currentIndex())) or (not (channel is None)))
        self.channel_selector.currentIndexChanged.connect(
            self.on_channel_selector_changed)

    def set_extra_items(self):
        self.async_check = QCheckBox(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-async"), self)
        self.async_check.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-async-tooltip"))
        self.async_check.setObjectName(ObjNames.SETTINGS_WINDOW_ASYNC_CHECK)
        self.async_check.setChecked(self.conf.get("async", False))
        self.async_check.stateChanged.connect(
            self.on_async_check_changed)
        self.debug_check = QCheckBox(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-debug"), self)
        self.debug_check.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-debug-tooltip"))
        self.debug_check.setObjectName(ObjNames.SETTINGS_WINDOW_DEBUG_CHECK)
        self.debug_check.setChecked(self.conf.get("debug", False))
        self.debug_check.stateChanged.connect(
            self.on_debug_check_changed)
        self.gui_check = QCheckBox(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-gui"), self)
        self.gui_check.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-gui-tooltip"))
        self.gui_check.setObjectName(ObjNames.SETTINGS_WINDOW_GUI_CHECK)
        self.gui_check.setChecked(self.conf.get("gui", True))
        self.gui_check.stateChanged.connect(
            self.on_gui_check_changed)
        self.lang_title = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-lang-title"), self)
        self.lang_selector = QComboBox(self)
        self.lang_selector.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-lang-selector-tooltip"))
        self.lang_selector.setObjectName(ObjNames.SETTINGS_WINDOW_LANG)
        for item in LANGS:
            self.lang_selector.addItem(item, item)
        self.lang_selector.setCurrentIndex(
            LANGS.index(self.conf.get("lang", "zh-cn")))
        self.lang_selector.currentIndexChanged.connect(
            self.on_lang_selector_changed)

    def set_proxy_widgets(self):
        self.proxy_label = QLabel(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-proxy-title"), self)
        self.proxy_list = ProxyTableWidget(0, self, **self.conf)

    def set_operate_btns(self):
        self.save_btn = QPushButton(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-save"), self)
        self.save_btn.setToolTip(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-save-tooltip"))
        self.save_btn.setObjectName(ObjNames.SETTINGS_WINDOW_SAVE)
        self.save_btn.clicked.connect(
            self.on_save_btn_clicked)
        self.cancel_btn = QPushButton(get_lang(self.conf.get(
            "lang", "zh-cn"), "ui-config-window-cancel"), self)
        self.cancel_btn.setObjectName(ObjNames.SETTINGS_WINDOW_CANCEL)
        self.cancel_btn.clicked.connect(self.close)

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

    def on_browser_selector_changed(self, idx: int):
        self.conf.update({"browser": self.browser_selector.currentData()})
        self.channel_selector.setEnabled(not bool(idx))
        self.on_channel_selector_changed(idx)

    def on_channel_selector_changed(self, idx: int):
        if self.channel_selector.isEnabled():
            self.conf.update({"channel": self.channel_selector.currentData()})
        else:
            self.conf.update({"channel": None})

    def on_lang_selector_changed(self, idx: int):
        self.conf.update({"lang": LANGS[idx]})

    def on_async_check_changed(self, state: Qt.CheckState):
        self.conf.update({"async": state == Qt.Checked})

    def on_debug_check_changed(self, state: Qt.CheckState):
        self.conf.update({"debug": state == Qt.Checked})

    def on_gui_check_changed(self, state: Qt.CheckState):
        self.conf.update({"gui": state == Qt.Checked})

    def on_save_btn_clicked(self):
        with open(get_config_path("config.json"), "w", encoding="utf-8") as writer:
            dump(self.conf, writer, sort_keys=True, indent=4)
        self.close()

    def on_executable_btn_clicked(self):
        result = QFileDialog.getOpenFileName(self, get_lang(
            self.conf.get("lang", "zh-cn"), "ui-config-window-executable-browse-title"))
        if result[0] != "":
            self.executable_input.setText(result[0])
            self.conf.update({"executable_path": result[0]})
        elif self.conf.get("executable_path") != "":
            self.executable_input.setText(result[0])
            self.conf.update({"executable_path": None})

    def on_executable_input_edit_finished(self):
        if isfile(self.executable_input.text()):
            self.conf.update({"executable_path": self.executable_input.text()})
        if self.executable_input.text() == "" and self.conf.get("executable_path") != "":
            self.conf.update({"executable_path": None})

    def on_skipped_items_input_edit_finished(self):
        input_text = self.skipped_items_input.text()
        input_items = input_text.split(
            ANSWER_CONNECTOR) if input_text != "" else []
        for i in range(len(input_items)):
            input_items[i] = input_items[i].strip()
        self.conf.update(
            {"skipped_items": input_items})


__all__ = ["SettingsWindow"]
