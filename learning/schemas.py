from dataclasses import dataclass
from typing import Any

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_RATINGS = {"again", "hard", "good", "easy"}


class LearningError(ValueError):
    """Stable domain error raised for invalid learning inputs."""


@dataclass(frozen=True)
class LearningSettings:
    flashcard_count: int = 8
    quiz_count: int = 5
    min_sentence_length: int = 24
    max_sentence_length: int = 280

    def __post_init__(self) -> None:
        if not 1 <= self.flashcard_count <= 30:
            raise LearningError("flashcard_count must be between 1 and 30")
        if not 1 <= self.quiz_count <= 30:
            raise LearningError("quiz_count must be between 1 and 30")


def normalize_documents(documents: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(documents, list) or not documents:
        raise LearningError("documents must be a non-empty list")

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(documents):
        if not isinstance(raw, dict):
            raise LearningError(f"document {index} must be an object")
        document_id = str(raw.get("id") or raw.get("document_id") or "").strip()
        content = str(raw.get("content") or raw.get("text") or "").strip()
        title = str(raw.get("title") or raw.get("filename") or f"Document {index + 1}").strip()
        if not document_id:
            raise LearningError(f"document {index} is missing id")
        if document_id in seen:
            raise LearningError(f"duplicate document id: {document_id}")
        if not content:
            continue
        seen.add(document_id)
        normalized.append({"id": document_id, "title": title, "content": content})

    if not normalized:
        raise LearningError("documents contain no usable text")
    return normalized
