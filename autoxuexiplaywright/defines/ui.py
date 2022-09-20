import base64
from autoxuexiplaywright.defines import core
from autoxuexiplaywright.utils import storage


OPACITY = 0.9
UI_CONF = storage.get_config_path(core.APPID+".ini")
UI_ICON = base64.b64decode(
    """iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAADeUlEQVRIie2WbWhWZRjH/5vnCaIPQSNMocYTjD70MjWWYumYQ2tiG1YoSkzLaVRQiLZyFUQfil6s5UgGg4Fk
        hhiuxd7SvTrcRDcjpfq4F9CtfGboBN15nnN+fbjceXp8XiYY2YfdcOBwn+u6fv/7uq/7uk+WK6HbMLJvB3QWPAtOGKFz5+X81+DQxs2S78m7BdCcG2GuRKaHkrXgurBhE66Er7t
        hxZqMPgn+9y+Awz9AXz8MDQXzGcF8uhvG/zCnsvU2d/IUXLtG7AbbqATlFXgSMQnK1kNPL7S24SsLStdB/4nMYFaVQfGzxCQ8Cc6dh+XP2Lf6fbDn67htQRHU1sHoKABoPigH3t
        gBeQXXs3QHjI2DctKDfTmQuxAmJ6FoNeyuhj8vwJmzoAfhyhW8BHvB4hWwcDn8csbEPPYkaH5cXGc3vLglgZME5pPPLU1ffGWrvRABz7PVRCZg1/sJ4MBvxzvw3gf2/uZOuHTZ0
        l+6Dhoak+yTwW/tgsHT9t7aBnkF4OTFBVz8C1zX9rGyCrqPmcCfjgappaExEMfAYEqhKVItqK3Dnd7f5zdCRxd8/Blsfc3Aq8osaHmFiQk/DpOTRKeLLBaDRYWw+rkgCzOCg5UX
        lkBXD2x73YK99AoMDcGS4rjN3lrYsAkeWQqjo/F5zbOMHGkHzUsZP6mBOHIU+v6wtGyxvKJCqfW4nKZmKZwrLxxW9ERH3Dj3AWlRvnSyXYpMyJEUKq9QVGN2yS/IV1RjqTtKUAx
        LV8LmbVaB11XS1GxF9Y+DH6zqvkftCJ0asMx09VgcsC1SGLqPpe0RBu7rt32prEr46El2Hn/7HVpaoaeX6DR4STGMjIDutXO7shSmpuDtd20BV69C25EZwL4P7Z3JnWjZ09apXB
        e++RbWvJAyiCfB8DBsrzSB1TVW8fsPzACu3xfvTPlPwdEOU3zpsjWSkrVpA0QlaG6BL/fAxEU4eMji7D+Q1DQyVnVMgrp62PKqBT39cyAqZfXX7IWch2FgEHqPQ3OLzY+N46fxc
        SWSrlhfUvbWl+VJN/f7OTUldX4nNTZJjiOvqlKhg4ekSESxDG4p73ZfklNdI+XcI82dK911Z9oA/s7tyo7FpOER6eyvmpNXIPm+1PBjZsHpUuFKdln09cNDT6S1cSX48KOU/TjT
        k+XeZEb/7fH//9mbBd/q+BuapkzTsaP4XQAAAABJRU5ErkJggg=="""
)
UI_WIDTH = 1024
UI_HEIGHT = 768


class ObjNames:
    MAIN = "main"
    CENTRAL_WIDGET = "central"
    TITLE = "title"
    SCORE = "score"
    CLOSE = "close"
    MINIMIZE = "minimize"
    ONTOP = "ontop"
    LOG_PANEL = "logpanel"
    LOG_PANEL_SCROLL = "logpanelscroll"
    START = "start"
    SETTINGS = "config"
    QR_LABEL = "qrlabel"
    SETTINGS_WINDOW = "config_main"
    SETTINGS_WINDOW_TITLE = "config_title"
    SETTINGS_WINDOW_BROWSER_SELECTOR = "browser"
    SETTINGS_WINDOW_CHANNEL_SELECTOR = "channel"
    SETTINGS_WINDOW_EXECUTABLE_INPUT = "browser_executable"
    SETTINGS_WINDOW_ASYNC_CHECK = "async"
    SETTINGS_WINDOW_DEBUG_CHECK = "debug"
    SETTINGS_WINDOW_GUI_CHECK = "gui"
    SETTINGS_WINDOW_LANG = "lang"
    SETTINGS_WINDOW_SAVE = "save"
    SETTINGS_WINDOW_CANCEL = "cancel"
    SETTINGS_WINDOW_EDIT = "edit"
    SETTINGS_WINDOW_PROXY = "proxy"
    SETTINGS_WINDOW_PROXY_HEADER = "header"


SPLIT_TITLE_SIZE = 30
SETTING_BROWSER_ITEMS = ["chromium", "firefox", "webkit"]
SETTING_ITEM_NAMES = {
    "msedge": "Microsoft Edge", "msedge-beta": "Microsoft Edge Beta", "msedge-dev": "Microsoft Edge Dev",
    "chrome": "Google Chrome", "chrome-beta": "Google Chrome Beta", "chrome-dev": "Google Chrome Dev",
    "chromium": "Google Chromium", "chromium-beta": "Google Chromium Beta", "chromium-dev": "Google Chromium Dev"
}
PROXY_REGEX = r"(https?|socks[45])://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"
NOTIFY_SECS = 5
