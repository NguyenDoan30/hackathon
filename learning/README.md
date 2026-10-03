# Learning / Quiz / Flashcard / Progress — Người 5

Module này chỉ phụ trách logic học tập. Không sửa FastAPI router, database, frontend,
AI Smart Context hoặc File Processing của các thành viên khác.

## Backend contract

Module khớp trực tiếp với `LearningProvider` của backend:

```python
flashcards(documents) -> list[dict]
quiz(documents) -> list[dict]
grade(questions, answers) -> dict
```

Provider để Backend load:

```text
learning.backend_adapter:BackendLearningProvider
```

Có thể đặt trong cấu hình production của Backend:

```text
LEARNING_PROVIDER=learning.backend_adapter:BackendLearningProvider
```

## Chức năng

### Flashcard
Tạo flashcard từ nội dung tài liệu đã được Backend xác thực, loại trùng và gắn difficulty.

### Quiz
Sinh câu hỏi trắc nghiệm deterministic có ID ổn định, options, correct_answer và explanation.
Backend hiện tại chịu trách nhiệm loại đáp án đúng trước khi gửi quiz ra Frontend.

### Grading
Kiểm tra đầy đủ đáp án, lựa chọn hợp lệ và trả `correct`, `total`, `score`, `feedback`
đúng contract của Backend.

### Progress
`calculate_progress(...)` tổng hợp flashcard review và quiz attempts để tính retention,
điểm trung bình, điểm gần nhất và recommendation. Persistence vẫn thuộc Backend.

## Ranh giới trách nhiệm

- Người 1: Frontend.
- Người 2: FastAPI, authentication, database, persistence.
- Người 3: AI / Smart Context / Summary / Tutor.
- Người 4: PDF, OCR, audio/transcript.
- Người 5: Flashcard, quiz, grading, learning progress.

Module không gọi Gemini và không cần API key. Nội dung quiz/flashcard hiện là extractive
và deterministic để demo/test ổn định. Có thể thay implementation sau nhưng nên giữ nguyên
`BackendLearningProvider` contract để tránh ảnh hưởng thành viên khác.

## Test

Từ root repo:

```powershell
python -m unittest discover -s learning/tests
```
