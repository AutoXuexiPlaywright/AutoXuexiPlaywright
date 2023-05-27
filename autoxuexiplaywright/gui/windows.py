from queue import Queue
from magic import from_buffer
from typing import TypeVar
from os.path import isfile
from PySide6.QtGui import QMouseEvent, QPixmap, QIcon, QRegularExpressionValidator
from PySide6.QtCore import QFile, QPointF, QSettings, QThread, Qt, QRegularExpression, QDir
from PySide6.QtWidgets import QCheckBox, QVBoxLayout, QInputDialog, QLabel, QSystemTrayIcon, QLineEdit, QPlainTextEdit, QPushButton, QHBoxLayout, QWidget, QComboBox, QFileDialog, QGridLayout
# Relative imports
from .objects import SubProcess
from ..defines import APPNAME
from ..languages import get_language_string
from ..storage import get_config_path, get_resources_path
from ..config import get_runtime_config, serialize_config
from ..processors.common import ANSWER_CONNECTOR
from ..processors.common.answer.utils import split_text, is_valid_answer

_SettingsValueType = TypeVar("_SettingsValueType", int, str, float, bool)
_QObjectType = TypeVar("_QObjectType")

_ICON_FILE_NAME = "icon.png"
_QSS_FILE_NAME = "ui.qss"
_OPACITY = 0.9
_UI_CONFIG_PATH = get_config_path(APPNAME+".ini")
_UI_WIDTH = 1024
_UI_HEIGHT = 768
_START_BTN_SIZE = 8
_SETTINGS_BTN_SIZE = 2
_NOTIFY_SECS = 5
_SPLIT_TITLE_SIZE = 35
_VALID_BROWSERS = ["chromium", "firefox", "webkit"]
_VALID_CHANNELS = {
    "msedge": "Microsoft Edge", "msedge-beta": "Microsoft Edge Beta", "msedge-dev": "Microsoft Edge Dev",
    "chrome": "Google Chrome", "chrome-beta": "Google Chrome Beta", "chrome-dev": "Google Chrome Dev",
    "chromium": "Chromium", "chromium-beta": "Chromium Beta", "chromium-dev": "Chromium Dev"}
_PROXY_PRETTY_NAMES = {
    "server": ("ui-config-window-proxy-address", "ui-config-window-proxy-address-tooltip"),
    "username": ("ui-config-window-proxy-username", "ui-config-window-proxy-username-tooltip"),
    "password": ("ui-config-window-proxy-password", "ui-config-window-proxy-password-tooltip"),
    "bypass": ("ui-config-window-proxy-bypass", "ui-config-window-proxy-bypass-tooltip")
}
_PROXY_REGEX = r"(https?|socks[45])://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"


class _QObjectIDs():
    MAIN = "main"
    TITLE = "title"
    TRAY = "tray"
    CLOSE = "close"
    MINIMIZE = "minimize"
    ONTOP = "ontop"
    LOG_PANEL = "logpanel"
    LOG_PANEL_SCROLL = "logpanelscroll"
    START = "start"
    SETTINGS = "config"
    QR_LABEL = "qrlabel"
    SCORE = "score"
    SETTINGS_WINDOW = "config_main"
    SETTINGS_WINDOW_TITLE = "config_title"
    SETTINGS_WINDOW_BROWSER_SELECTOR = "browser"
    SETTINGS_WINDOW_CHANNEL_SELECTOR = "channel"
    SETTINGS_WINDOW_EXECUTABLE_INPUT = "browser_executable"
    SETTINGS_WINDOW_SKIPPED_ITEMS = "skipped_items"
    SETTINGS_WINDOW_ASYNC_CHECK = "async"
    SETTINGS_WINDOW_DEBUG_CHECK = "debug"
    SETTINGS_WINDOW_GUI_CHECK = "gui"
    SETTINGS_WINDOW_LANG = "lang"
    SETTINGS_WINDOW_GET_VIDEO = "get_video"
    SETTINGS_WINDOW_PROXY = {
        "server": "proxy_addr",
        "username": "proxy_username",
        "password": "proxy_password",
        "bypass": "proxy_bypass"
    }


class _QWidgetExtended(QWidget):
    def findChildWithProperType(self, type: type[_QObjectType], name: str = "", options: Qt.FindChildOption = Qt.FindChildOption.FindDirectChildrenOnly) -> _QObjectType | None:
        """Find Child QObject with proper type

        This is for making static type checker happy

        Args:
            type (type[_QObjectType]): The type of target QObject
            name (str, optional): The object name of target QObject. Defaults to "".
            options (Qt.FindChildOption, optional): Find option. Defaults to Qt.FindChildOption.FindDirectChildrenOnly.

        Returns:
            _QObjectType | None: The target QObject, or None if not found
        """
        result = self.findChild(type, name, options)
        if isinstance(result, type):
            return result


class _QSettingsExtended(QSettings):
    def getValueWithProperType(self, key: str, default: _SettingsValueType) -> _SettingsValueType:
        """Get value with proper type

        This is for making static type checker happy

        Args:
            key (str): The key of the value
            default (_SettingsValueType): The default value if not found

        Returns:
            _SettingsValueType: The value or the default value
        """
        value = self.value(key, default, type(default))
        if isinstance(value, type(default)):
            return value
        return default


class QFramelessWidget(_QWidgetExtended):
    def __init__(self, parent: QWidget | None = None, f: Qt.WindowType = Qt.WindowType.FramelessWindowHint) -> None:
        super().__init__(parent, f)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.isMaximized() and not self.isFullScreen() and event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()
        return super().mousePressEvent(event)


class _QComboBoxWithLabel(QFramelessWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        layout = QHBoxLayout()
        self.label = QLabel(self)
        self.label.setObjectName("self-label")
        self.comboBox = QComboBox(self)
        self.comboBox.setObjectName("self-combobox")
        layout.addWidget(self.label)
        layout.addWidget(self.comboBox)
        self.setLayout(layout)
        self.setStyleSheet(parent.styleSheet())


class _QLineEditWithLabelOnly(QFramelessWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        layout = QHBoxLayout()
        self.label = QLabel(self)
        self.label.setObjectName("self-label")
        self.lineEdit = QLineEdit(self)
        self.lineEdit.setObjectName("self-lineedit")
        layout.addWidget(self.label)
        layout.addWidget(self.lineEdit)
        self.setLayout(layout)
        self.setStyleSheet(parent.styleSheet())


class _QLineEditWithBrowseButton(_QLineEditWithLabelOnly):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.browseBtn = QPushButton(self)
        self.browseBtn.setObjectName("self-browsebtn")
        self.layout().addWidget(self.browseBtn)
        self.setStyleSheet(parent.styleSheet())


class _QLineEditWithLabelMultiple(QFramelessWidget):
    def __init__(self, parent: QWidget, keys: list[str], split: int = 0):
        super().__init__(parent)
        self._lineEditsWithLabel: dict[str, _QLineEditWithLabelOnly] = {}
        layout = QGridLayout()
        x = 0
        y = 0
        for key in keys:
            currentLineEditWithLabel = _QLineEditWithLabelOnly(self)
            self._lineEditsWithLabel[key] = currentLineEditWithLabel
            currentLineEditWithLabel.lineEdit.setObjectName(key)
            currentLineEditWithLabel.label.setObjectName(key)
            if split > 0 and x > split-1:
                y = y+1
                x = x-split
            layout.addWidget(currentLineEditWithLabel, y, x)
            x = x+1
        self.setLayout(layout)
        self.setStyleSheet(parent.styleSheet())

    def findLabelByKey(self, key: str) -> QLabel | None:
        lineEditWithLabel = self._lineEditsWithLabel.get(key)
        if lineEditWithLabel != None:
            return lineEditWithLabel.label

    def findLineEditByKey(self, key: str) -> QLineEdit | None:
        lineEditWithLabel = self._lineEditsWithLabel.get(key)
        if lineEditWithLabel != None:
            return lineEditWithLabel.lineEdit


class SettingsWindow(QFramelessWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent, parent.windowFlags() | Qt.WindowType.Dialog)
        self.setObjectName(_QObjectIDs.SETTINGS_WINDOW)
        mainLayout = QVBoxLayout()
        # title
        title = QLabel(get_language_string("ui-config-window-title"), self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName(_QObjectIDs.SETTINGS_WINDOW_TITLE)
        mainLayout.addWidget(title)

        contentsLayout = QVBoxLayout()

        browserSettingsLayout = QHBoxLayout()
        config = get_runtime_config()
        # browser selector
        browserSelector = _QComboBoxWithLabel(self)
        browserSelector.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_BROWSER_SELECTOR)
        browserSelector.label.setText(
            get_language_string("ui-config-window-browser-title"))
        browserSelector.comboBox.setToolTip(get_language_string(
            "ui-config-window-browser-selector-tooltip"))
        browserSelector.comboBox.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_BROWSER_SELECTOR)
        for i in _VALID_BROWSERS:
            browserSelector.comboBox.addItem(i.title(), i)
        browserSelector.comboBox.setCurrentIndex(
            _VALID_BROWSERS.index(config.browser_id))
        browserSelector.comboBox.currentIndexChanged.connect(  # type: ignore
            self._onBrowserSelectorIndexChanged)
        browserSettingsLayout.addWidget(browserSelector)
        # channelSelector
        channelSelector = _QComboBoxWithLabel(self)
        channelSelector.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_CHANNEL_SELECTOR)
        channelSelector.label.setText(
            get_language_string("ui-config-window-channel-title"))
        channelSelector.comboBox.setToolTip(get_language_string(
            "ui-config-window-channel-selector-tooltip"))
        channelSelector.comboBox.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_CHANNEL_SELECTOR)
        for k, v in _VALID_CHANNELS.items():
            channelSelector.comboBox.addItem(v, k)
        if config.browser_channel != None:
            channelSelector.comboBox.setCurrentIndex(
                list(_VALID_CHANNELS.keys()).index(config.browser_channel))
        channelSelector.setEnabled(
            (not bool(browserSelector.comboBox.currentIndex())) or (
                config.browser_channel != None))
        channelSelector.comboBox.currentIndexChanged.connect(  # type: ignore
            self._onChannelSelectorIndexChanged
        )
        browserSettingsLayout.addWidget(channelSelector)
        contentsLayout.addLayout(browserSettingsLayout)
        # executableSetting
        executableSettingWidget = _QLineEditWithBrowseButton(self)
        executableSettingWidget.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_EXECUTABLE_INPUT)
        executableSettingWidget.label.setText(
            get_language_string("ui-config-window-executable-label"))
        executableSettingWidget.lineEdit.setToolTip(
            get_language_string("ui-config-window-executable-tooltip"))
        executableSettingWidget.lineEdit.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_EXECUTABLE_INPUT)
        if config.executable_path != None:
            executableSettingWidget.lineEdit.setText(config.executable_path)
        executableSettingWidget.lineEdit.editingFinished.connect(  # type: ignore
            self._onBrowserExecutableEditFinished
        )
        executableSettingWidget.browseBtn.setText(
            get_language_string("ui-config-window-executable-browse-text"))
        executableSettingWidget.browseBtn.setToolTip(
            get_language_string("ui-config-window-executable-browse-tooltip"))
        executableSettingWidget.browseBtn.clicked.connect(  # type: ignore
            self._onBrowserExecutableBrowseButtonClicked
        )
        contentsLayout.addWidget(executableSettingWidget)
        # skipped items
        skippedItemsWidget = _QLineEditWithLabelOnly(self)
        skippedItemsWidget.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_SKIPPED_ITEMS)
        skippedItemsWidget.label.setText(get_language_string(
            "ui-config-window-skipped-items-label"))
        skippedItemsWidget.lineEdit.setToolTip(get_language_string(
            "ui-config-window-skipped-items-tooltip") % ANSWER_CONNECTOR)
        skippedItemsWidget.lineEdit.setObjectName(
            _QObjectIDs.SETTINGS_WINDOW_SKIPPED_ITEMS)
        if len(config.skipped) > 0:
            skippedItemsWidget.lineEdit.setText(
                ANSWER_CONNECTOR.join(config.skipped))
        skippedItemsWidget.lineEdit.editingFinished.connect(  # type: ignore
            self._onSkippedItemsEditFinished
        )
        contentsLayout.addWidget(skippedItemsWidget)
        # extra items
        extraSettingsLayout = QHBoxLayout()
        asyncMode = QCheckBox(get_language_string(
            "ui-config-window-async"), self)
        asyncMode.setToolTip(get_language_string(
            "ui-config-window-async-tooltip"))
        asyncMode.setObjectName(_QObjectIDs.SETTINGS_WINDOW_ASYNC_CHECK)
        asyncMode.setChecked(config.async_mode)
        asyncMode.stateChanged.connect(  # type: ignore
            self._onAsyncModeChanged)
        extraSettingsLayout.addWidget(asyncMode)
        debugMode = QCheckBox(get_language_string(
            "ui-config-window-debug"), self)
        debugMode.setToolTip(get_language_string(
            "ui-config-window-debug-tooltip"))
        debugMode.setObjectName(_QObjectIDs.SETTINGS_WINDOW_DEBUG_CHECK)
        debugMode.setChecked(config.debug)
        debugMode.stateChanged.connect(  # type: ignore
            self._onDebugModeChanged
        )
        extraSettingsLayout.addWidget(debugMode)
        guiMode = QCheckBox(get_language_string("ui-config-window-gui"), self)
        guiMode.setToolTip(get_language_string("ui-config-window-gui-tooltip"))
        guiMode.setObjectName(_QObjectIDs.SETTINGS_WINDOW_GUI_CHECK)
        guiMode.setChecked(config.gui)
        guiMode.stateChanged.connect(  # type: ignore
            self._onGUIModeChanged
        )
        extraSettingsLayout.addWidget(guiMode)
        getVideo = QCheckBox(get_language_string(
            "ui-config-window-get-video"), self)
        getVideo.setToolTip(get_language_string(
            "ui-config-window-get-video-tooltip"))
        getVideo.setObjectName(_QObjectIDs.SETTINGS_WINDOW_GET_VIDEO)
        getVideo.setChecked(config.get_video)
        getVideo.stateChanged.connect(  # type: ignore
            self._onGetVideoChanged
        )
        extraSettingsLayout.addWidget(getVideo)
        langSetting = _QComboBoxWithLabel(self)
        langSetting.setObjectName(_QObjectIDs.SETTINGS_WINDOW_LANG)
        langSetting.label.setText(
            get_language_string("ui-config-window-lang-title"))
        langSetting.comboBox.setToolTip(get_language_string(
            "ui-config-window-lang-selector-tooltip"))
        langSetting.comboBox.setObjectName(_QObjectIDs.SETTINGS_WINDOW_LANG)
        langIDs = self._getLangIDs()
        for i in langIDs:
            langSetting.comboBox.addItem(i, i)
        if config.lang in langIDs:
            langSetting.comboBox.setCurrentIndex(langIDs.index(config.lang))
        langSetting.comboBox.currentIndexChanged.connect(  # type: ignore
            self._onLanguageSettingIndexChanged
        )
        extraSettingsLayout.addWidget(langSetting)

        contentsLayout.addLayout(extraSettingsLayout)
        # proxy setting
        proxySetting = _QLineEditWithLabelMultiple(
            self, list(_PROXY_PRETTY_NAMES.keys()), 2)
        for key in _PROXY_PRETTY_NAMES.keys():
            label = proxySetting.findLabelByKey(key)
            if label != None:
                label.setText(get_language_string(_PROXY_PRETTY_NAMES[key][0]))
            lineEdit = proxySetting.findLineEditByKey(key)
            if lineEdit != None:
                lineEdit.setToolTip(get_language_string(
                    _PROXY_PRETTY_NAMES[key][1]))
                lineEdit.setObjectName(_QObjectIDs.SETTINGS_WINDOW_PROXY[key])
        serverLineEdit = proxySetting.findLineEditByKey("server")
        if serverLineEdit != None:
            serverLineEdit.setValidator(
                QRegularExpressionValidator(QRegularExpression(_PROXY_REGEX))
            )
        passwordLineEdit = proxySetting.findLineEditByKey("password")
        if passwordLineEdit != None:
            passwordLineEdit.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        contentsLayout.addWidget(proxySetting)
        # save/cancel
        operateLayout = QHBoxLayout()
        saveBtn = QPushButton(get_language_string(
            "ui-config-window-save"), self)
        saveBtn.setToolTip(get_language_string(
            "ui-config-window-save-tooltip"))
        saveBtn.clicked.connect(self._onSaveButtonClicked)  # type: ignore

        operateLayout.addWidget(saveBtn)
        cancelBtn = QPushButton(get_language_string(
            "ui-config-window-cancel"), self)
        cancelBtn.setToolTip(get_language_string(
            "ui-config-window-cancel-tooltip"))
        cancelBtn.clicked.connect(self._onCancelButtonClicked)  # type: ignore

        operateLayout.addWidget(cancelBtn)

        contentsLayout.addLayout(operateLayout)
        mainLayout.addLayout(contentsLayout)
        self.setLayout(mainLayout)
        self.setStyleSheet(parent.styleSheet())

    def _getLangIDs(self) -> list[str]:
        langSuffix = ".json"
        langDir = QDir(get_resources_path("lang"))
        langDir.setNameFilters(["*"+langSuffix])
        return [langFile.replace(langSuffix, "")
                for langFile in langDir.entryList()]

    def _onBrowserSelectorIndexChanged(self, index: int):
        browserSelector = self.findChildWithProperType(
            _QComboBoxWithLabel, _QObjectIDs.SETTINGS_WINDOW_BROWSER_SELECTOR)
        if browserSelector != None:
            config = get_runtime_config()
            config.browser_id = browserSelector.comboBox.currentData()
        channelSelector = self.findChildWithProperType(
            _QComboBoxWithLabel, _QObjectIDs.SETTINGS_WINDOW_CHANNEL_SELECTOR)
        if channelSelector != None:
            channelSelector.setEnabled(not bool(index))
            self._onChannelSelectorIndexChanged(index)

    def _onChannelSelectorIndexChanged(self, index: int):
        channelSelector = self.findChildWithProperType(
            _QComboBoxWithLabel, _QObjectIDs.SETTINGS_WINDOW_CHANNEL_SELECTOR)
        if channelSelector != None:
            config = get_runtime_config()
            if channelSelector.isEnabled():
                config.browser_channel = channelSelector.comboBox.currentData()
            else:
                config.browser_channel = None

    def _onBrowserExecutableEditFinished(self):
        executableSettingWidget = self.findChildWithProperType(
            _QLineEditWithBrowseButton)
        if executableSettingWidget != None:
            config = get_runtime_config()
            path = executableSettingWidget.lineEdit.text()
            if isfile(path):
                config.executable_path = path
            elif path != "":
                config.executable_path = None

    def _onBrowserExecutableBrowseButtonClicked(self):
        executableSettingWidget = self.findChildWithProperType(
            _QLineEditWithBrowseButton)
        if executableSettingWidget != None:
            config = get_runtime_config()
            result: str = QFileDialog.getOpenFileName(  # type: ignore
                self, get_language_string("ui-config-window-executable-browse-title"))[0]
            if result != "":
                config.executable_path = result
            elif config.executable_path != None:
                config.executable_path = None
            executableSettingWidget.lineEdit.setText(result)  # type: ignore

    def _onSkippedItemsEditFinished(self):
        skippedItemsWidget = self.findChildWithProperType(
            _QLineEditWithLabelOnly)
        if skippedItemsWidget != None:
            get_runtime_config().skipped = skippedItemsWidget.lineEdit.text().split(ANSWER_CONNECTOR)

    def _onAsyncModeChanged(self, state: Qt.CheckState):
        get_runtime_config().async_mode = Qt.CheckState(state) == Qt.CheckState.Checked

    def _onDebugModeChanged(self, state: Qt.CheckState):
        get_runtime_config().debug = Qt.CheckState(state) == Qt.CheckState.Checked

    def _onGUIModeChanged(self, state: Qt.CheckState):
        get_runtime_config().gui = Qt.CheckState(state) == Qt.CheckState.Checked

    def _onGetVideoChanged(self, state: Qt.CheckState):
        get_runtime_config().get_video = Qt.CheckState(state) == Qt.CheckState.Checked

    def _onLanguageSettingIndexChanged(self, index: int):
        languageSetting = self.findChildWithProperType(
            _QComboBoxWithLabel, _QObjectIDs.SETTINGS_WINDOW_LANG)
        if languageSetting != None:
            get_runtime_config().lang = self._getLangIDs()[index]

    def _onSaveButtonClicked(self):
        path: str = QFileDialog.getSaveFileName(self, get_language_string(  # type: ignore
            "ui-config-window-save-title"), get_config_path(""), "JSON(*.json)")[0]
        if path != "":
            config = get_runtime_config()
            serialize_config(config, path)  # type: ignore

    def _onCancelButtonClicked(self):
        self.close()


class MainWindow(QFramelessWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(get_resources_path(_ICON_FILE_NAME)))
        self.setWindowTitle(APPNAME)
        self.setWindowOpacity(_OPACITY)
        self.setObjectName(_QObjectIDs.MAIN)
        self.resize(_UI_WIDTH, _UI_HEIGHT)
        settings = _QSettingsExtended(
            _UI_CONFIG_PATH, QSettings.Format.IniFormat, self)
        self.move(settings.getValueWithProperType("UI/x", 0),
                  settings.getValueWithProperType("UI/y", 0))
        if settings.getValueWithProperType("UI/ontop", False):
            self.setWindowFlags(self.windowFlags() |
                                Qt.WindowType.WindowStaysOnTopHint)

        tray = QSystemTrayIcon(self.windowIcon(), self)
        tray.setToolTip(APPNAME)
        tray.setObjectName(_QObjectIDs.TRAY)
        tray.activated.connect(self._onTrayActivated)  # type: ignore

        mainLayout = QVBoxLayout(self)
        # title
        titleLayout = QHBoxLayout()
        title = QLabel(APPNAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName(_QObjectIDs.TITLE)
        score = QLabel(get_language_string("ui-score-text") % (0, 0))
        score.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        score.setObjectName(_QObjectIDs.SCORE)
        titleLayout.addWidget(score)
        titleLayout.addWidget(title)
        controlLayout = QHBoxLayout()
        closeBtn = QPushButton("", self)
        closeBtn.setObjectName(_QObjectIDs.CLOSE)
        closeBtn.setToolTip(get_language_string("ui-close-btn-tooltip"))
        closeBtn.clicked.connect(self.close)  # type: ignore
        minimizeBtn = QPushButton("", self)
        minimizeBtn.setObjectName(_QObjectIDs.MINIMIZE)
        minimizeBtn.setToolTip(get_language_string("ui-minimize-btn-tooltip"))
        minimizeBtn.clicked.connect(self.showMinimized)  # type: ignore
        onTopCheck = QCheckBox("", self)
        onTopCheck.setObjectName(_QObjectIDs.ONTOP)
        onTopCheck.setToolTip(get_language_string("ui-ontop-checkbox-tooltip"))
        onTopCheck.stateChanged.connect(  # type: ignore
            self._onOnTopStateChanged)
        controlLayout.addWidget(onTopCheck)
        controlLayout.addWidget(minimizeBtn)
        controlLayout.addWidget(closeBtn)
        controlLayout.setAlignment(Qt.AlignmentFlag.AlignRight)
        titleLayout.addLayout(controlLayout)
        # log panel
        logPanel = QPlainTextEdit(self)
        logPanel.setObjectName(_QObjectIDs.LOG_PANEL)
        logPanel.setToolTip(get_language_string("ui-logpanel-default-tooltip"))
        logPanel.setReadOnly(True)
        logPanel.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        logPanel.verticalScrollBar().setObjectName(_QObjectIDs.LOG_PANEL_SCROLL)
        # start/setting buttons
        startLayout = QHBoxLayout()
        startBtn = QPushButton(get_language_string(
            "ui-start-btn-tooltip"), self)
        startBtn.setToolTip(get_language_string("ui-start-btn-tooltip"))
        startBtn.setObjectName(_QObjectIDs.START)
        startBtn.clicked.connect(self._onStartBtnClicked)  # type: ignore
        settingsBtn = QPushButton(get_language_string(
            "ui-settings-btn-tooltip"), self)
        settingsBtn.setToolTip(get_language_string("ui-settings-btn-tooltip"))
        settingsBtn.setObjectName(_QObjectIDs.SETTINGS)
        settingsBtn.clicked.connect(self._onSettingsBtnClicked)  # type: ignore
        startLayout.addWidget(startBtn, _START_BTN_SIZE)
        startLayout.addWidget(settingsBtn, _SETTINGS_BTN_SIZE)
        # construct ui
        mainLayout.addLayout(titleLayout)
        mainLayout.addWidget(logPanel)
        mainLayout.addLayout(startLayout)
        mainLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(mainLayout)
        # jobs
        qThread = QThread(self)
        self.subProcess = SubProcess()
        self.subProcess.moveToThread(qThread)
        self.subProcess.jobFinishedSignal.connect(self._onJobFinished)
        self.subProcess.updateLogSignal.connect(logPanel.appendPlainText)
        self.subProcess.updateStatusSignal.connect(self._onStatusUpdated)
        self.subProcess.pauseThreadSignal.connect(self._onManualInputRequired)
        self.subProcess.qrControlSignal.connect(self._onQRBytesRecived)
        self.subProcess.updateScoreSignal.connect(self._onScoreUpdated)
        qThread.started.connect(self.subProcess.start)  # type: ignore
        qThread.finished.connect(self._onQThreadFinished)  # type: ignore
        # stylesheets
        qssFile = QFile(get_resources_path(_QSS_FILE_NAME))
        qssFile.open(QFile.OpenModeFlag.ReadOnly)
        self.setStyleSheet(qssFile.readAll().data().decode())
        qssFile.close()

    def show(self):
        tray = self.findChildWithProperType(QSystemTrayIcon, _QObjectIDs.TRAY)
        if tray != None:
            tray.show()
        super().show()

    def close(self) -> bool:
        tray = self.findChildWithProperType(QSystemTrayIcon, _QObjectIDs.TRAY)
        if tray != None:
            tray.hide()
        return super().close()

    def showMinimized(self):
        tray = self.findChildWithProperType(QSystemTrayIcon, _QObjectIDs.TRAY)
        if tray != None:
            if tray.isSystemTrayAvailable():
                tray.show()
                self.hide()
                return
        super().showMinimized()

    def _onJobFinished(self, data: str):
        thread = self.findChildWithProperType(QThread)
        if thread != None:
            thread.quit()
        tray = self.findChildWithProperType(QSystemTrayIcon, _QObjectIDs.TRAY)
        if tray != None:
            tray.showMessage(get_language_string("ui-tray-notification-title-info"),
                             data, QSystemTrayIcon.MessageIcon.Information, _NOTIFY_SECS*1000)

    def _onQThreadFinished(self):
        logPanel = self.findChildWithProperType(
            QPlainTextEdit, _QObjectIDs.LOG_PANEL)
        if logPanel != None:
            logPanel.setToolTip(get_language_string(
                "ui-logpanel-default-tooltip"))
        startBtn = self.findChildWithProperType(QPushButton, _QObjectIDs.START)
        if startBtn != None:
            startBtn.setEnabled(True)
            startBtn.setToolTip(get_language_string("ui-start-btn-tooltip"))
            startBtn.setText(get_language_string("ui-start-btn-tooltip"))
        qrLabel = self.findChildWithProperType(QLabel, _QObjectIDs.QR_LABEL)
        if qrLabel != None:
            qrLabel.close()

    def _onManualInputRequired(self, data: tuple[str, Queue[list[str]]]):
        title = data[0]
        queue = data[1]
        dialogTitle = get_language_string(
            "ui-manual-input-required") % ANSWER_CONNECTOR
        parsedTitle = title.split("\n")
        questionTitle = "\n".join(split_text(
            parsedTitle[0], _SPLIT_TITLE_SIZE))
        questionTips = "\n".join(split_text(parsedTitle[1], _SPLIT_TITLE_SIZE))
        answersFromPage = "\n".join(split_text(
            parsedTitle[2], _SPLIT_TITLE_SIZE)) if len(parsedTitle) > 2 else ""
        fullText = "\n".join(
            [dialogTitle, questionTitle, questionTips, answersFromPage])
        answerText, requireResult = QInputDialog.getText(
            self, dialogTitle, fullText, QLineEdit.EchoMode.Normal, "", Qt.WindowType.FramelessWindowHint)
        if requireResult:
            answer = [answerTextPart.strip() for answerTextPart in answerText.strip().split(
                ANSWER_CONNECTOR) if is_valid_answer(answerTextPart.strip())]
        else:
            answer = []
        queue.put(answer)
        self.subProcess.wait.wakeAll()

    def _onQRBytesRecived(self, qr: bytes):
        existingQRLabel = self.findChildWithProperType(
            QLabel, _QObjectIDs.QR_LABEL)
        if isinstance(existingQRLabel, QLabel):
            existingQRLabel.close()
        if from_buffer(qr, True).startswith("image"):
            qrLabel = QLabel(self)
            qrLabel.setObjectName(_QObjectIDs.QR_LABEL)
            qrLabel.setWindowModality(Qt.WindowModality.WindowModal)
            qrLabel.setStyle(self.style())
            pixmap = QPixmap()
            pixmap.loadFromData(qr)
            qrLabel.setPixmap(pixmap)
            qrLabel.resize(pixmap.size())
            qrLabel.move(round((self.width()-qrLabel.width())/2),
                         round((self.height()-qrLabel.height())/2))
            qrLabel.show()

    def _onScoreUpdated(self, score: list[int]):
        score = score[:2]
        if score != [-1, -1]:
            scoreLabel = self.findChildWithProperType(
                QLabel, _QObjectIDs.SCORE)
            if scoreLabel != None:
                scoreLabel.setText(
                    get_language_string("ui-score-text") % tuple(score))

    def _onOnTopStateChanged(self, state: Qt.CheckState):
        settings = self.findChildWithProperType(_QSettingsExtended)
        if settings != None:
            match Qt.CheckState(state):
                case Qt.CheckState.Checked:
                    self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
                    settings.setValue("UI/ontop", True)
                    self.show()
                case Qt.CheckState.Unchecked:
                    self.setWindowFlag(
                        Qt.WindowType.WindowStaysOnTopHint, False)
                    settings.setValue("UI/ontop", False)
                    self.show()
                case _:
                    pass

    def _onStartBtnClicked(self):
        startBtn = self.findChildWithProperType(QPushButton, _QObjectIDs.START)
        if startBtn != None:
            startBtn.setEnabled(False)
            startBtn.setText(get_language_string(
                "ui-start-btn-processing-tooltip"))
            startBtn.setToolTip(get_language_string(
                "ui-start-btn-processing-tooltip"))
        qThread = self.findChildWithProperType(QThread)
        if qThread != None:
            qThread.start()

    def _onSettingsBtnClicked(self):
        settingsWindow = self.findChildWithProperType(
            SettingsWindow, _QObjectIDs.SETTINGS)
        if settingsWindow == None:
            settingsWindow = SettingsWindow(self)
        settingsWindow.resize(round(self.width()*3/4),
                              round(self.height()*3/8))
        settingsWindow.move(self.x()+round((self.width()-settingsWindow.width())/2),
                            self.y()+round((self.height()-settingsWindow.height())/2))
        settingsWindow.show()

    def _onTrayActivated(self, reason: QSystemTrayIcon.ActivationReason):
        match QSystemTrayIcon.ActivationReason(reason):
            case QSystemTrayIcon.ActivationReason.Trigger:
                self.setHidden(not self.isHidden())
            case _:
                pass

    def _onStatusUpdated(self, status: str):
        logPanel = self.findChildWithProperType(
            QPlainTextEdit, _QObjectIDs.LOG_PANEL)
        if logPanel != None:
            logPanel.setToolTip(get_language_string(
                "ui-status-tooltip") % status)
