import re
from enum import Enum


APPID = "AutoXuexiPlaywright"

DEFAULT_CONF = {
    "debug": False,
    "browser": "firefox",
    "channel": None,
    "proxy": None,
    "async": False,
    "gui": True,
    "lang": "zh-cn"
}


ANSWER_SLEEP_MAX_SECS = 3.0
ANSWER_SLEEP_MIN_SECS = 1.5
LOGIN_RETRY_TIMES = 5
READ_TIME_SECS = 60
WAIT_NEW_PAGE_SECS = 5
WAIT_PAGE_SECS = 300
WAIT_RESULT_SECS = 5
CHECK_ELEMENT_TIMEOUT_SECS = 5
VIDEO_REQUEST_REGEX = re.compile(r"https://.+.(m3u8|mp4)")
LOGGING_FMT = "%(asctime)s-%(levelname)s-%(message)s"
LOGGING_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
LANGS = ["zh-cn"]
NEWS_RANGE = range(1, 2)
VIDEO_RANGE = range(2, 4)
TEST_RANGE = range(4, 7)


class ProcessType(Enum):
    UNKNOWN = 0
    NEWS = 1
    VIDEO = 2
    TEST = 3


PROCESS_SLEEP_MIN = 0.0
PROCESS_SLEEP_MAX = 5.0
ANSWER_CONNECTOR = "#"
EXTRA_MODULES_NAMESPACE = "autoxuexiplaywright.extra_modules"
EXTRA_ANSWER_SOURCES_NAMESPACE = EXTRA_MODULES_NAMESPACE+".answer_sources"
MOD_EXT = ".as.py"
