from autoxuexiplaywright import appid

__all__ = ["AnswerSource"]
PRIORITY_INF = 999


class AnswerSource():
    def __init__(self) -> None:
        self.name = "SourceTemplate"
        self.author = appid
        # This will be set by script when it is imported.
        self.priority = PRIORITY_INF

    def get_answer(self, title: str) -> list[str]:
        raise NotImplementedError(
            "Please Implement this Method yourself.",
            "If you are a common user, please report this problem to %s" % self.author
        )

    def close(self) -> None:
        pass
