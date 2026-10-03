import unittest

from learning import BackendLearningProvider, LearningError, calculate_progress


DOCUMENTS = [
    {
        "id": "doc-1",
        "title": "OOP",
        "content": (
            "Đóng gói là cơ chế che giấu trạng thái bên trong của đối tượng. "
            "Kế thừa cho phép lớp con tái sử dụng thuộc tính và hành vi của lớp cha. "
            "Đa hình cho phép cùng một giao diện có nhiều cách triển khai khác nhau. "
            "Trừu tượng hóa tập trung vào đặc điểm quan trọng và bỏ qua chi tiết không cần thiết. "
            "Lớp là khuôn mẫu dùng để tạo ra các đối tượng trong lập trình hướng đối tượng."
        ),
    }
]


class LearningProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = BackendLearningProvider()

    def test_flashcards_match_backend_contract(self):
        cards = self.provider.flashcards(DOCUMENTS)
        self.assertGreaterEqual(len(cards), 1)
        for card in cards:
            self.assertEqual(set(card), {"question", "answer", "difficulty"})
            self.assertIn(card["difficulty"], {"easy", "medium", "hard"})

    def test_quiz_and_grade_are_consistent(self):
        quiz = self.provider.quiz(DOCUMENTS)
        answers = {q["id"]: q["correct_answer"] for q in quiz}
        grade = self.provider.grade(quiz, answers)
        self.assertEqual(grade["correct"], len(quiz))
        self.assertEqual(grade["total"], len(quiz))
        self.assertEqual(grade["score"], 100.0)
        self.assertEqual(len(grade["feedback"]), len(quiz))

    def test_wrong_answers_score_zero(self):
        quiz = self.provider.quiz(DOCUMENTS)
        answers = {
            q["id"]: next(option for option in q["options"] if option != q["correct_answer"])
            for q in quiz
        }
        grade = self.provider.grade(quiz, answers)
        self.assertEqual(grade["correct"], 0)
        self.assertEqual(grade["score"], 0.0)

    def test_grade_rejects_missing_answer(self):
        quiz = self.provider.quiz(DOCUMENTS)
        with self.assertRaises(LearningError):
            self.provider.grade(quiz, {})

    def test_progress(self):
        result = calculate_progress(
            flashcard_reviews=[{"rating": "good"}, {"rating": "again"}, {"rating": "easy"}],
            quiz_attempts=[{"score": 60}, {"score": 90}],
        )
        self.assertEqual(result["flashcards_reviewed"], 3)
        self.assertAlmostEqual(result["flashcard_retention"], 66.67)
        self.assertEqual(result["average_quiz_score"], 75.0)
        self.assertEqual(result["latest_quiz_score"], 90.0)


if __name__ == "__main__":
    unittest.main()
