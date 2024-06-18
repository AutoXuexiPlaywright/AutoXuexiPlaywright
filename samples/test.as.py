"""Sample Module."""

from typing_extensions import override
from autoxuexiplaywright.sdk.answer import AnswerSource
from autoxuexiplaywright.sdk.module import module_entrance


@module_entrance
class TestSource(AnswerSource):
    """Sample AnswerSource module."""

    @override
    def get_answer(self, title: str) -> list[str]:
        return []

    @property
    @override
    def name(self) -> str:
        return "Test"

    @property
    @override
    def author(self) -> str:
        return "Test"


# Simply place this file to modules folder under data directory,
# we will load this file when start processing.
