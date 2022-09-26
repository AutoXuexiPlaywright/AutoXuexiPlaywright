import platform
from autoxuexiplaywright.gui import ui
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTranslator, QLibraryInfo
from autoxuexiplaywright.defines import core

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(core.APPID)

__all__ = ["start"]


def lang_to_locale(lang: str) -> str:
    parts = lang.split("-")
    extra = "_"+parts[1].upper() if len(parts) > 1 else ""
    return parts[0]+extra


def start(argv: list, **kwargs):
    app = QApplication(argv)
    lang = lang_to_locale(kwargs.get("lang", "zh-cn"))
    translator = QTranslator()
    translator.load(
        "qt_"+lang, QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(translator)
    main_window = ui.MainWindow(**kwargs)
    main_window.show()
    app.exec_()
