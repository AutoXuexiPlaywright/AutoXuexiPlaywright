"""AnswerSource class."""

from abc import abstractmethod
from .module import Module


class AnswerSource(Module):
    """Class which can get answer by give question."""
    @abstractmethod
    def get_answer(self, title: str) -> list[str]:
        """Get answer.

        Args:
            title(str): Question title

        Returns:
            list[str]: The answers
        """
