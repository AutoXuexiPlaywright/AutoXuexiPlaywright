from platform import system
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator

from autoxuexiplaywright.gui.ui import MainWindow
from autoxuexiplaywright.defines.core import APPID
from autoxuexiplaywright.utils.config import Config

if system() == "Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID) # type: ignore


def lang_to_locale(lang: str) -> str:
    parts = lang.split("-")
    extra = "_"+parts[1].upper() if len(parts) > 1 else ""
    return parts[0]+extra


def start(argv: list[str]):
    app = QApplication(argv)
    translator = QTranslator()
    translator.load("qt_"+lang_to_locale(Config.get_instance().lang))
    app.installTranslator(translator)
    main_window = MainWindow()
    main_window.show()
    app.exec_()


__all__ = ["start"]
