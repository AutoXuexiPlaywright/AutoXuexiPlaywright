from autoxuexiplaywright.gui import lang_to_locale

_maps = {
    "ar": "ar",
    "zh-cn": "zh_CN"
}


def test_lang_to_locale():
    for k, v in _maps.items():
        assert lang_to_locale(k) == v
