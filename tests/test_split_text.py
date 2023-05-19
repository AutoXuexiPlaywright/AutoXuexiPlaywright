from autoxuexiplaywright.processors.common.answer.utils import split_text


_string = "abc"
_io_map: dict[int, list[str]] = {
    1: ["a", "b", "c"],
    2: ["ab", "c"],
    3: ["abc"],
    4: ["abc"]
}


def test_split_text():
    for k, v in _io_map.items():
        assert split_text(_string, k) == v
