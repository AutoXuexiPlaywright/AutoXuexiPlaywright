from platform import system
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTranslator

from autoxuexiplaywright.gui.ui import MainWindow
from autoxuexiplaywright.defines.core import APPID
from autoxuexiplaywright.utils.config import Config

if system() == "Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)


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
