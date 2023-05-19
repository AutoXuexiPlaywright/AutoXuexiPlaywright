from autoxuexiplaywright.sdk import AnswerSource


class TestSource(AnswerSource):

    def get_answer(self, title: str) -> list[str]:
        """Get answer from title given
        Args:
            title (str): The question's title without space
        Returns:
            list[str]: The list of answers
        """
        return []

    @property
    def name(self) -> str:
        """The name of this source
        """
        return "Test"

    @property
    def author(self) -> str:
        """The author of this source
        """
        return "Test"

# Simply place this file to modules folder under data directory, we will load this file when start processing.
