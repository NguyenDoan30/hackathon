# AI / Smart Context

Module của thành viên phụ trách AI trong nhóm 5 người. Thư mục này tách biệt với backend, frontend, xử lý file/audio và learning.

## Commit đầu tiên: cấu trúc và dữ liệu

Hiện có Source, TranscriptSegment, Turn, Settings, Chunk và Result; validation đầu vào và serialize kết quả. Chưa có provider Gemini, retrieval, chat hay Summary trong commit này. Các phần đã có ở demo độc lập sẽ được đưa lên theo những commit tiếp theo, dùng thời gian commit thực tế.

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

Kiểm thử commit đầu không gọi Google hoặc đọc API key. `.env.example` chỉ có trường cấu hình trống; `.env` và bytecode được bỏ qua bởi `.gitignore` trong module.

## Phân công và các commit tiếp theo

- Người 1 giữ giao diện chính; demo riêng của AI sẽ được bổ sung sau.
- Người 2 giữ backend/router/database/auth. Người 3 chỉ bổ sung module này.
- Người 4 cung cấp văn bản/transcript từ PDF/OCR/audio; module AI không tự upload hoặc nhận dạng ghi âm.
- Người 5 giữ quiz/flashcard/progress.

Các bước kế tiếp: truy xuất/context/prompt; Gemini và lỗi/quota; dịch vụ chat/Summary; adapter backend, demo, kiểm thử và tài liệu.

Nhánh backend/database hiện đề xuất AIProvider constructor không tham số, summarize(documents) và chat(question, documents, history). Adapter tương thích sẽ nằm trong module AI ở commit sau; chưa sửa backend để ghép vào. Khi bổ sung adapter cần ánh xạ ID nguồn và history đúng hợp đồng backend, giữ key phía server và kiểm tra dữ liệu đã được backend xác thực.
