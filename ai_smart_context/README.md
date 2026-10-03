# AI / Smart Context

Module của thành viên phụ trách AI trong nhóm 5 người. Thư mục này tách biệt với backend, frontend, xử lý file/audio và learning.

## Phạm vi hiện tại: dữ liệu, Smart Context và provider

Commit 01 cung cấp Source, TranscriptSegment, Turn, Settings, Chunk và Result; validation đầu vào và serialize kết quả. Commit 02 bổ sung retrieval.py, context.py và prompts.py. Commit 03 bổ sung GeminiProvider, MockProvider, cấu hình và phân loại lỗi/quota. Dịch vụ chat/Summary chưa có trong nhánh ở bước này. Các phần đã có ở demo độc lập được đưa lên theo từng commit với thời gian thực tế.

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

Các bước kế tiếp: dịch vụ chat/Summary; adapter backend, demo, kiểm thử và tài liệu.

Nhánh backend/database hiện đề xuất AIProvider constructor không tham số, summarize(documents) và chat(question, documents, history). Adapter tương thích sẽ nằm trong module AI ở commit sau; chưa sửa backend để ghép vào. Khi bổ sung adapter cần ánh xạ ID nguồn và history đúng hợp đồng backend, giữ key phía server và kiểm tra dữ liệu đã được backend xác thực.

## Provider và cấu hình

GeminiProvider nhận api_key, model, Settings và transport (urllib hoặc curl). Key và model cũng có thể lấy từ GEMINI_API_KEY và GEMINI_MODEL phía server. Không cố định tên model vì quyền sử dụng phụ thuộc tài khoản. read_gemini_config(path) đọc file cấu hình UTF-8 giới hạn 8 KB, chỉ chấp nhận hai biến trên; biến môi trường không rỗng được ưu tiên. Hàm không tự thay đổi môi trường, và GeminiProvider không tự đọc file .env.

Ví dụ kết nối cho backend; generate trả về đối tượng JSON từ model, chưa kiểm tra nội dung/citation của dịch vụ:

```python
from ai_smart_context import GeminiProvider, read_gemini_config

config = read_gemini_config()  # .env trong module, hoặc truyền path rõ ràng
provider = GeminiProvider(api_key=config['GEMINI_API_KEY'],
                          model=config['GEMINI_MODEL'], transport='curl')
```

- Key gửi bằng header HTTPS. Curl nhận key và payload qua stdin, không qua tham số dòng lệnh hoặc file tạm. Xác minh chứng chỉ giữ bật; không đi theo redirect; bỏ qua curlrc. Transport curl cần curl có hỗ trợ `%header{retry-after}` (curl 7.84 trở lên); máy Windows của demo đã kiểm tra khả năng này.
- Phản hồi giới hạn 2 MB, JSON phải là object và candidate phải kết thúc STOP. Thought parts không đưa vào kết quả.
- Lỗi HTTP 401/403 và lỗi chứng chỉ không retry. HTTP 500/502/503/504 và lỗi mạng có retry hữu hạn theo Settings, mặc định tối đa 3 lần gọi với thời gian chờ 1 rồi 2 giây; mỗi lần có timeout riêng. Không phải deadline chung cho cả thao tác.
- HTTP 429 không tự retry. ProviderError có code, quota_kind, retry_after_seconds, retryable. Quota ngày hoặc quota bằng 0 được đánh dấu không retry; quota phút/không rõ loại trả metadata cho bên gọi quyết định. Đọc Retry-After và RetryInfo, chọn thời gian chờ dài hơn. Khi không có thời gian chờ, thông báo 60 giây chỉ là dự phòng của demo, không phải đảm bảo quota phục hồi; provider không có timer hay bộ điều phối quota giữa các request.
- MockProvider trích xuất nguồn và đánh dấu simulated=True. Đây là chế độ kiểm thử offline; không tự chuyển từ Gemini sang mock khi lỗi.

Kiểm thử provider dùng phản hồi giả và tiến trình Python con để kiểm tra giới hạn output/timeout của transport. Không gọi API thật, không đọc file .env thật và không tiêu thụ quota. Việc kiểm tra citation và phối hợp retrieval với provider sẽ nằm trong commit dịch vụ.
