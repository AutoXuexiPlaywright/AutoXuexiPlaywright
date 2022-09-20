import platform
from autoxuexiplaywright.gui import ui
from qtpy.QtWidgets import QApplication
from autoxuexiplaywright.defines import core

if platform.system() == "Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(core.APPID)
    
__all__=["start"]


def start(*args, **kwargs):
    app = QApplication(list(args))
    main_window = ui.MainWindow(**kwargs)
    main_window.show()
    app.exec_()