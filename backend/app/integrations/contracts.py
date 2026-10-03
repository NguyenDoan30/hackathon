from pathlib import Path
from typing import Protocol

class FileProvider(Protocol):
    def process(self, path: Path, media_type: str) -> dict:
        """Return {content: str, transcript: str | None}. Own external timeouts."""
        ...

class AIProvider(Protocol):
    def summarize(self, documents: list[dict]) -> dict:
        """Return {summary: str, key_points: list[str]}."""
        ...
    def chat(self, question: str, documents: list[dict], history: list[dict]) -> dict:
        """Return {answer: str, sources: list[document_id]}."""
        ...

class LearningProvider(Protocol):
    def flashcards(self, documents: list[dict]) -> list[dict]: ...
    def quiz(self, documents: list[dict]) -> list[dict]: ...
    def grade(self, questions: list[dict], answers: dict[str, str]) -> dict:
        """Return {correct, total, score, feedback}. Scoring belongs to Person 5."""
        ...
