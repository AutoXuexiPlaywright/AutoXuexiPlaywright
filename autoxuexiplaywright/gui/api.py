from platform import system
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator

from autoxuexiplaywright.gui.ui import MainWindow
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.defines.core import APPID
from autoxuexiplaywright.defines.ui import DESKTOP_FILE_ID


def lang_to_locale(lang: str) -> str:
    parts = lang.split("-")
    extra = "_"+parts[1].upper() if len(parts) > 1 else ""
    return parts[0]+extra


def start(argv: list[str]):
    match system():
        case "Windows":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore
                APPID)
        case "Linux":
            QApplication.setDesktopFileName(DESKTOP_FILE_ID)
        case _:
            pass
    app = QApplication(argv)
    translator = QTranslator()
    translator.load("qt_"+lang_to_locale(Config.get_instance().lang))
    app.installTranslator(translator)
    main_window = MainWindow()
    main_window.show()
    app.exec()


__all__ = ["start"]
