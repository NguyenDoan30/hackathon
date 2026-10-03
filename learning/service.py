from .flashcards import generate_flashcards
from .grading import grade_quiz
from .quiz import generate_quiz
from .schemas import LearningSettings


class LearningService:
    """Backend-compatible implementation of Person 5's learning contract."""

    def __init__(self, settings: LearningSettings | None = None) -> None:
        self.settings = settings or LearningSettings()

    def flashcards(self, documents: list[dict]) -> list[dict]:
        return generate_flashcards(documents, self.settings)

    def quiz(self, documents: list[dict]) -> list[dict]:
        return generate_quiz(documents, self.settings)

    def grade(self, questions: list[dict], answers: dict[str, str]) -> dict:
        return grade_quiz(questions, answers)
