# Changes since legacy version

1. Data storage has been changed.  
    In the legacy version, the program will record your history to avoid processing too many times. But now, we removed that, because this program may be used by more than one account.  
    Also, we have changed data storage path:  
    - For Windows, config, data, temp files are placed at `%USERPROFILE%\AppData\Local\AutoXuexiPlaywright`. 
    - For Linux, we follow XDG standard and place config at `${XDG_CONFIG_HOME:-${HOME}/.config}/AutoXuexiPlaywright`, place data at `${XDG_DATA_HOME:-${HOME}/.local/share/AutoXuexiPlaywright}`, place temp files at `${XDG_CACHE_HOME:-${HOME}/.cache/AutoXuexiPlaywright}`.  
    Linux Special: there is also a system wide data path: `/usr/share/autoxuexiplaywright`, this is used for that some data, like modules and so on, may be provided by other packages.
    - For MacOS, we place config at `${HOME}/Library/Preferences/AutoXuexiPlaywright`, place data at `${HOME}/Library/Application Support/AutoXuexiPlaywright`, place temp files at `${HOME}/Library/Caches/AutoXuexiPlaywright`.
    - For other platforms, we place files like Linux without `XDG_*_HOME` set.
2. We introduce a module interface, which is for answer source.  
    To use this, simply write a python script which contains a subclass of `autoxuexiplaywright.sdk.AnswerSource` and implement its `get_answer()` method, place that script at `modules` folder under data path, with the name ends with `.as.py`. Note: those modules belongs to third-party contents and we are NOT responsible for any situation results by those contents. You should always check those modules yourself. Also, due to that our license is `GPL3`, if you are a module developer, please keep your work opensourced like us.
3. We also developped an overlay mechanism.  
    You can override any file under `resources` folder by place a file with the same name under where we place data. For example, if you want to override `zh-cn.json` on Windows, you can place a new `%USERPROFILE%\AppData\Local\AutoXuexiPlaywright\lang\zh-cn.json` and we will use your file instead ours. This may be useful when you are a Linux user because you can modify resoources as you like without having root privilege.
