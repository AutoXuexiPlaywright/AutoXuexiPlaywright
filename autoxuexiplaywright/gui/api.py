from platform import system
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTranslator, QLibraryInfo

from autoxuexiplaywright.gui.ui import MainWindow
from autoxuexiplaywright.defines.core import APPID

if system() == "Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)


def lang_to_locale(lang: str) -> str:
    parts = lang.split("-")
    extra = "_"+parts[1].upper() if len(parts) > 1 else ""
    return parts[0]+extra


def start(argv: list, **kwargs):
    app = QApplication(argv)
    translator = QTranslator()
    translator.load("qt_"+lang_to_locale(kwargs.get("lang", "zh-cn")),
                    QLibraryInfo.location(QLibraryInfo.LibrariesPath.TranslationsPath))
    app.installTranslator(translator)
    main_window = MainWindow(**kwargs)
    main_window.show()
    app.exec_()


__all__ = ["start"]
