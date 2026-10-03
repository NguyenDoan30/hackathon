# AI / Smart Context

Module của thành viên phụ trách AI trong nhóm 5 người. Thư mục này tách biệt với backend, frontend, xử lý file/audio và learning.

## Phạm vi hiện tại: dữ liệu và Smart Context

Commit 01 cung cấp Source, TranscriptSegment, Turn, Settings, Chunk và Result; validation đầu vào và serialize kết quả. Commit 02 bổ sung retrieval.py, context.py và prompts.py. Chưa có provider Gemini hoặc dịch vụ chat/Summary trong nhánh ở bước này. Các phần đã có ở demo độc lập được đưa lên theo từng commit với thời gian thực tế.

| Kiểu dữ liệu | Vai trò |
|---|---|
| Source | Văn bản tài liệu, ghi chú hoặc transcript của một bài học |
| TranscriptSegment | Đoạn bài giảng với timestamp tính bằng giây |
| Turn | Lượt hội thoại của một bài học |
| Settings | Ngân sách context/lịch sử, chia đoạn, timeout và retry |
| Chunk | Đoạn context có ID và nguồn |
| Result | Kết quả chat/tóm tắt, citations và trạng thái mô phỏng |

Nguồn có lesson_id nhưng việc kiểm tra quyền truy cập thuộc backend. Transcript thiếu timestamp được truyền bằng Source.text; không tạo mốc giả. Timestamp có trong segments phải khớp bản ghi thật. Các giới hạn input được kiểm tra trong schemas.py.

## Kiểm tra

Python >=3.10, thư viện chuẩn; không cần cài thêm package. Từ thư mục gốc repo:

```powershell
python -m unittest discover -s ai_smart_context/tests
```

Kiểm thử không gọi Google hoặc đọc API key. `.env.example` chỉ có trường cấu hình trống; `.env` và bytecode được bỏ qua bởi `.gitignore` trong module.

## Smart Context

- Lọc nguồn theo lesson_id trước khi chia đoạn; từ chối ID trùng và dữ liệu bài học quá giới hạn.
- Chia văn bản với overlap, giữ liên kết nguồn và timestamp có trong transcript. Khi có segments, ưu tiên segments để tránh lặp lại text.
- Tìm kiếm lexical BM25 có chuẩn hóa dấu tiếng Việt; truy vấn không có từ khớp hoặc chỉ trùng một từ trong câu nhiều từ được loại. Chưa có embeddings/vector database, nên paraphrase không trùng từ có thể không tìm được nguồn. Trùng nhiều từ chưa chứng minh nguồn đủ trả lời; dịch vụ AI ở commit sau vẫn phải kiểm tra và báo thiếu bằng chứng.
- Chọn context theo ngân sách JSON gồm cả metadata; nguồn quá dài được bỏ qua để xét đoạn ngắn hơn phía sau.
- Lịch sử chỉ dùng đúng bài học, giới hạn các lượt gần nhất và chủ đề cũ của người dùng. History là ngữ cảnh hội thoại, không phải bằng chứng kiến thức.
- Prompt tách sources/history/question thành dữ liệu JSON và yêu cầu dùng đúng citation ID. Đây là quy tắc prompt, không bảo đảm model chống được mọi prompt injection; kiểm tra đầu ra sẽ nằm trong dịch vụ AI ở commit sau.

Nhận diện follow-up hiện là heuristic cho các cụm như “dễ hiểu hơn”, “giải thích lại”, “ví dụ”; chưa phải bộ phân loại ý định. Những câu hỏi vừa có cụm follow-up vừa chuyển chủ đề cần được kiểm tra thêm khi ghép dịch vụ.

## Phân công và các commit tiếp theo

- Người 1 giữ giao diện chính; demo riêng của AI sẽ được bổ sung sau.
- Người 2 giữ backend/router/database/auth. Người 3 chỉ bổ sung module này.
- Người 4 cung cấp văn bản/transcript từ PDF/OCR/audio; module AI không tự upload hoặc nhận dạng ghi âm.
- Người 5 giữ quiz/flashcard/progress.

Các bước kế tiếp: Gemini và lỗi/quota; dịch vụ chat/Summary; adapter backend, demo, kiểm thử và tài liệu.

Nhánh backend/database hiện đề xuất AIProvider constructor không tham số, summarize(documents) và chat(question, documents, history). Adapter tương thích sẽ nằm trong module AI ở commit sau; chưa sửa backend để ghép vào. Khi bổ sung adapter cần ánh xạ ID nguồn và history đúng hợp đồng backend, giữ key phía server và kiểm tra dữ liệu đã được backend xác thực.
