from abc import ABC, abstractmethod


class Module(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...  # The name of your module

    @property
    @abstractmethod
    def author(self) -> str: ...  # The author of your module

    def start(self):  # Called when it is started
        pass

    def close(self):  # Called when it is going to be closed
        pass


class AnswerSource(Module):
    @abstractmethod
    def get_answer(self, title: str) -> list[str]: ...  # Core function
