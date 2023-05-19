from autoxuexiplaywright.processors.common.answer.utils import is_valid_answer

_test_items = {
    "": False,
    "a": True,
    "1": True,
    "测试": True,
    "c测试": True,
    "测试c": True,
    "测c试": True,
    " ": False
}


def test_is_valid_answer():
    for k, v in _test_items.items():
        assert is_valid_answer(k) == v
