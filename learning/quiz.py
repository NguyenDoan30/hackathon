import hashlib
import re

from .schemas import LearningError, LearningSettings
from .text import sentence_candidates, term_from_sentence


def _stable_id(document_id: str, text: str, index: int) -> str:
    digest = hashlib.sha256(f"{document_id}|{text}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"q_{digest}"


def _distractors(correct: str, pool: list[str]) -> list[str]:
    alternatives = [value for value in pool if value != correct]
    fallback = [
        "Không có thông tin này trong tài liệu",
        "Khái niệm hoàn toàn không liên quan",
        "Tất cả các phương án trên đều sai",
    ]
    result: list[str] = []
    for value in alternatives + fallback:
        value = value.strip()
        if value and value != correct and value not in result:
            result.append(value)
        if len(result) == 3:
            break
    return result


def generate_quiz(documents: list[dict], settings: LearningSettings) -> list[dict]:
    candidates = sentence_candidates(documents, settings)
    if len(candidates) < 1:
        raise LearningError("not enough usable text to generate quiz")

    answers = [item["text"] for item in candidates]
    questions: list[dict] = []
    for index, item in enumerate(candidates[: settings.quiz_count]):
        term = term_from_sentence(item["text"])
        correct = item["text"]
        distractors = _distractors(correct, answers)
        options = [correct, *distractors]
        # Stable rotation avoids always exposing the correct answer as option A,
        # while remaining deterministic for tests and repeatable demos.
        shift = int(hashlib.sha256(item["text"].encode("utf-8")).hexdigest()[:2], 16) % len(options)
        options = options[shift:] + options[:shift]
        questions.append({
            "id": _stable_id(item["document_id"], item["text"], index),
            "question": f"Phát biểu nào mô tả đúng nhất về {term}?",
            "options": options,
            "correct_answer": correct,
            "explanation": f"Đáp án được lấy trực tiếp từ tài liệu: {item['title']}.",
        })
    return questions
