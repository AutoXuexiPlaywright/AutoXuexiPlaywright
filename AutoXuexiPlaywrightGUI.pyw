import os
import sys
from PySide6.QtWidgets import QApplication
from AutoXuexiPlaywrightCore.AutoXuexiPlaywrightGUI import MainUI
if __name__=="__main__":
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    # 将工作目录转移到脚本所在目录，保证下面的相对路径都能正确找到文件
    app=QApplication(sys.argv)
    main_window=MainUI()
    main_window.show()
    sys.exit(app.exec())
