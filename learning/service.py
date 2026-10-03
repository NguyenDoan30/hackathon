from .flashcards import generate_flashcards
from .schemas import LearningSettings


class LearningService:
    """Backend-compatible implementation of Person 5's learning contract."""

    def __init__(self, settings: LearningSettings | None = None) -> None:
        self.settings = settings or LearningSettings()

    def flashcards(self, documents: list[dict]) -> list[dict]:
        return generate_flashcards(documents, self.settings)

    def quiz(self, documents: list[dict]) -> list[dict]:
        raise NotImplementedError("quiz is implemented in the next commit")

    def grade(self, questions: list[dict], answers: dict[str, str]) -> dict:
        raise NotImplementedError("grade is implemented in the next commit")
