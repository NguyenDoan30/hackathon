from collections import Counter

from .schemas import ALLOWED_RATINGS, LearningError


def calculate_progress(
    *,
    flashcard_reviews: list[dict] | None = None,
    quiz_attempts: list[dict] | None = None,
) -> dict:
    flashcard_reviews = flashcard_reviews or []
    quiz_attempts = quiz_attempts or []

    ratings = Counter()
    for review in flashcard_reviews:
        rating = str(review.get("rating", "")).lower()
        if rating not in ALLOWED_RATINGS:
            raise LearningError(f"invalid flashcard rating: {rating}")
        ratings[rating] += 1

    scores: list[float] = []
    for attempt in quiz_attempts:
        score = float(attempt.get("score", 0))
        if not 0 <= score <= 100:
            raise LearningError("quiz score must be between 0 and 100")
        scores.append(score)

    remembered = ratings["good"] + ratings["easy"]
    reviewed = sum(ratings.values())
    retention = round(100 * remembered / reviewed, 2) if reviewed else 0.0
    average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    latest_score = scores[-1] if scores else None

    if latest_score is None:
        recommendation = "Làm quiz đầu tiên để đánh giá mức độ hiểu bài."
    elif latest_score < 50:
        recommendation = "Học lại nội dung chính và ôn flashcard trước khi làm lại quiz."
    elif latest_score < 80:
        recommendation = "Ôn các flashcard chưa nhớ rồi làm thêm một lượt quiz."
    else:
        recommendation = "Kết quả tốt; có thể chuyển sang nội dung tiếp theo và ôn lại định kỳ."

    return {
        "flashcards_reviewed": reviewed,
        "flashcard_retention": retention,
        "quiz_attempts": len(scores),
        "average_quiz_score": average_score,
        "latest_quiz_score": latest_score,
        "recommendation": recommendation,
    }
