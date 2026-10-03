from .schemas import LearningError, LearningSettings
from .text import sentence_candidates, term_from_sentence


def generate_flashcards(documents: list[dict], settings: LearningSettings) -> list[dict]:
    candidates = sentence_candidates(documents, settings)
    if not candidates:
        raise LearningError("not enough usable text to generate flashcards")

    cards: list[dict] = []
    for item in candidates:
        term = term_from_sentence(item["text"])
        answer = item["text"]
        difficulty = "easy" if len(answer) < 90 else ("medium" if len(answer) < 170 else "hard")
        cards.append({
            "question": f"Hãy giải thích: {term}?",
            "answer": answer,
            "difficulty": difficulty,
        })
        if len(cards) >= settings.flashcard_count:
            break
    return cards
