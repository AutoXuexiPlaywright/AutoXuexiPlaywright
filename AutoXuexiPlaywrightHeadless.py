import os
from AutoXuexiPlaywrightCore import AutoXuexiPlaywrightCore

if __name__=="__main__":
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    # 将工作目录转移到脚本所在目录，保证下面的相对路径都能正确找到文件
    processor=AutoXuexiPlaywrightCore.XuexiProcessor()
    processor.start()