from autoxuexiplaywright.sdk import AnswerSource


class TestSource(AnswerSource):
    def __init__(self) -> None:
        self.name = "Test"
        self.author = "Test"
        self.priority = 1  # This is useless because program will set this.

    def get_answer(self, title: str) -> list[str]:
        # Implement this method yourself, you can use whatever you want,
        # title is question's title without space
        # return value should be the list of answers
        return super().get_answer(title)

# Simply place this file to modules folder under data directory, we will load this file when start processing.
