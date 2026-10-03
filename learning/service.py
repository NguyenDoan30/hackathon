from .schemas import LearningSettings


class LearningService:
    """Facade implementing the backend LearningProvider method names."""

    def __init__(self, settings: LearningSettings | None = None) -> None:
        self.settings = settings or LearningSettings()

    def flashcards(self, documents: list[dict]) -> list[dict]:
        raise NotImplementedError("flashcards is implemented in the next commit")

    def quiz(self, documents: list[dict]) -> list[dict]:
        raise NotImplementedError("quiz is implemented in the next commits")

    def grade(self, questions: list[dict], answers: dict[str, str]) -> dict:
        raise NotImplementedError("grade is implemented in the next commits")
