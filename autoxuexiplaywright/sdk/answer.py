from abc import abstractmethod
from .module import Module


class AnswerSource(Module):
    @abstractmethod
    def get_answer(self, title: str) -> list[str]: ...  # Core function