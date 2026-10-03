# Giao diện ghép module cho nhóm 5 người

Backend chỉ chỉnh `backend/`. Đây là đề xuất hợp đồng phiên bản 1.0 để nhóm review trước khi ghép; chưa sửa hay gửi thông điệp tới module của đồng đội.

## Nạp module mà không sửa code của người khác

Các provider là class đồng bộ, constructor không có tham số. Mỗi người giữ implementation trong module của mình. Module phải import được trong môi trường backend (cài package của nhóm hoặc cấu hình PYTHONPATH trong phiên chạy). Không cần đặt code AI/file/learning bên trong app/api.

Ví dụ `.env` (tên module minh họa, không phải đường dẫn đã tồn tại):

```dotenv
APP_MODE=production
AI_PROVIDER=team_ai.provider:StudyAI
FILE_PROVIDER=team_files.provider:FileProcessor
LEARNING_PROVIDER=team_learning.provider:LearningEngine
```

Backend fail startup nếu đường dẫn đã cấu hình không import được hoặc thiếu phương thức. Provider để trống vẫn cho API CRUD chạy; gọi chức năng tương ứng trả 503/failed. `APP_MODE=demo` chọn toàn bộ fixture riêng và không gọi provider thật.

## Người 4 — File Processing

```python
from pathlib import Path

class FileProcessor:
    def process(self, path: Path, media_type: str) -> dict:
        # Đọc PDF/OCR/audio trong module của bạn.
        return {"content": "Nội dung đã trích xuất", "transcript": None}
```

- Input: đường dẫn tuyệt đối tới file backend đã lưu và media_type do backend xác định từ đuôi file.
- Output: content không rỗng, tối đa 1.000.000 ký tự; audio có thể thêm transcript cùng giới hạn.
- Không ghi database. Không xóa/di chuyển file. Backend lưu Document.content và Transcript.
- Chữ ký upload chỉ được kiểm tra cơ bản; provider kiểm tra và xử lý định dạng sâu hơn.
- Set timeout cho OCR/STT bên ngoài; raise exception nếu thất bại. Backend đánh dấu failed, lưu code chung và cho retry.

## Người 3 — AI / Smart Context

`documents` là danh sách `{id, filename, content}` chỉ gồm tài liệu ready của đúng bài học. Backend không tự làm RAG hoặc tóm tắt context; provider chủ động chọn/chunk/truy xuất ngữ cảnh theo giới hạn mô hình.

```python
class StudyAI:
    def summarize(self, documents: list[dict]) -> dict:
        return {"summary":"Tóm tắt", "key_points":["Ý chính"]}

    def chat(self, question: str, documents: list[dict], history: list[dict]) -> dict:
        return {"answer":"Câu trả lời", "sources":[documents[0]["id"]]}
```

`history`: tối đa 12 cặp question/answer gần nhất, thứ tự cũ → mới. Không có API key hoặc dữ liệu tài khoản khác. `sources` là ID tài liệu trong documents; có thể rỗng khi không tìm được thông tin. Backend từ chối ID nguồn ngoài bài học. Summary/answer tối đa 100.000 ký tự, key_points tối đa 100 mục.

Provider đặt timeout hữu hạn (gợi ý 30 giây), kiểm soát quota/context và giữ API key trong môi trường backend. Provider phải tự xử lý việc tài liệu chứa yêu cầu độc hại, trả lời ngoài context, follow-up và thông báo không tìm thấy thông tin; backend không giả vờ giải quyết chất lượng RAG.

## Người 5 — Learning

```python
class LearningEngine:
    def flashcards(self, documents: list[dict]) -> list[dict]:
        return [{"question":"Câu hỏi", "answer":"Đáp án", "difficulty":"medium"}]

    def quiz(self, documents: list[dict]) -> list[dict]:
        return [{"id":"q1", "question":"Câu hỏi", "options":["A","B"],
                 "answer":"A", "explanation":"Giải thích"}]

    def grade(self, questions: list[dict], answers: dict[str,str]) -> dict:
        return {"correct":1, "total":1, "score":100.0,
                "feedback":[{"question_id":"q1","correct":True,
                             "answer":"A","explanation":"Giải thích"}]}
```

Danh sách flashcard/quiz có 1–50 mục. difficulty: easy/medium/hard. Question ID duy nhất trong quiz; options có 2–6 lựa chọn khác nhau; answer phải thuộc options. MVP này hỗ trợ quiz trắc nghiệm một đáp án; tự luận, mindmap và spaced repetition chưa thuộc phần triển khai hiện tại.

Backend lưu câu hỏi cùng đáp án nội bộ, không trả answer/explanation trên GET quiz. Submit yêu cầu đủ key và option hợp lệ. Provider nhận questions đầy đủ để chấm bài; backend xác minh total bằng số câu, correct không vượt total và score khớp tỉ lệ đúng (sai số làm tròn ≤0,02).

Grade thuộc Người 5. `DemoLearning.grade` chỉ là fixture để kiểm thử hợp đồng. Backend lưu kết quả và tổng hợp trung bình/điểm cao nhất/số lần làm; chưa phân tích mạnh/yếu hoặc lên lịch ôn.

Tạo lại flashcard thay bộ đang hoạt động và cascade review cũ; quiz mới tạo phiên bản mới, giữ quiz cũ và lịch sử bài làm. Phải thống nhất chính sách này trước khi frontend gọi nút generate nhiều lần.

## Người 1 — Frontend

Dùng `API_CONTRACT.md` và Swagger. Login nhận access_token; truyền Bearer ở mọi request dữ liệu. Không đưa API key AI vào frontend, không chọn user_id bằng tay. Upload multipart, poll trạng thái, hiển thị lỗi; cần disable submit trong khi đang gửi.

Demo `app/demo/` là công cụ trình diễn backend riêng, không phải frontend cuối cùng. Nhóm có thể bỏ truy cập demo hoàn toàn khi ghép giao diện sản phẩm bằng APP_MODE=production.

## Quy trình ghép

1. Nhóm review tên API và input/output trong hai tài liệu này.
2. Mỗi người cung cấp provider riêng cùng dependency và ví dụ gọi.
3. Người 2 cấu hình đường dẫn trong .env local; test với file mẫu của Người 4 và câu hỏi của Người 3.
4. Người 5 kiểm tra nội dung và luồng học; backend sửa lỗi thuộc API/database.
5. Người 1 nối UI thật; cả nhóm test luồng upload → content → summary/chat → flashcard/quiz/progress.

Database không dùng chung giữa máy của 5 người; khi demo tích hợp chọn một backend server cho frontend gọi. Các provider chạy sync qua threadpool FastAPI hoặc background task trong process; phiên bản này chỉ chạy một worker. Hàng đợi bền vững, streaming chat, nhiều server và vector database là việc mở rộng sau MVP.
