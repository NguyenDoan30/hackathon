from .service import LearningService


class BackendLearningProvider:
    """Zero-argument provider loaded by backend/app/integrations/providers.py."""

    def __init__(self) -> None:
        self._service = LearningService()

    def flashcards(self, documents: list[dict]) -> list[dict]:
        return self._service.flashcards(documents)

    def quiz(self, documents: list[dict]) -> list[dict]:
        return self._service.quiz(documents)

    def grade(self, questions: list[dict], answers: dict[str, str]) -> dict:
        return self._service.grade(questions, answers)
