from .schemas import LearningError


def grade_quiz(questions: list[dict], answers: dict[str, str]) -> dict:
    if not isinstance(questions, list) or not questions:
        raise LearningError("questions must be a non-empty list")
    if not isinstance(answers, dict):
        raise LearningError("answers must be an object")

    ids = [str(q.get("id", "")).strip() for q in questions]
    if any(not qid for qid in ids) or len(set(ids)) != len(ids):
        raise LearningError("question ids must be present and unique")
    if set(answers) != set(ids):
        raise LearningError("answers must contain every question exactly once")

    correct = 0
    feedback: list[dict] = []
    for question in questions:
        qid = question["id"]
        options = question.get("options")
        expected = question.get("answer")
        selected = answers[qid]
        if not isinstance(options, list) or expected not in options:
            raise LearningError(f"invalid question: {qid}")
        if selected not in options:
            raise LearningError(f"invalid selected option for {qid}")

        is_correct = selected == expected
        correct += int(is_correct)
        feedback.append({
            "question_id": qid,
            "correct": is_correct,
            "selected_answer": selected,
            "correct_answer": expected,
            "explanation": str(question.get("explanation") or ""),
        })

    total = len(questions)
    return {
        "correct": correct,
        "total": total,
        "score": round(100.0 * correct / total, 2),
        "feedback": feedback,
    }
