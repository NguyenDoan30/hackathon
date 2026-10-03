# AI / Smart Context

Module của thành viên phụ trách AI trong nhóm 5 người. Thư mục này tách biệt với backend, frontend, xử lý file/audio và learning.

## Phạm vi hiện tại: dữ liệu, Smart Context, provider và dịch vụ

Commit 01 cung cấp Source, TranscriptSegment, Turn, Settings, Chunk và Result; validation đầu vào và serialize kết quả. Commit 02 bổ sung retrieval.py, context.py và prompts.py. Commit 03 bổ sung GeminiProvider, MockProvider, cấu hình và phân loại lỗi/quota. Commit 04 bổ sung StudyAssistant cho chat/Summary và kiểm tra đầu ra/citation. Các phần đã có ở demo độc lập được đưa lên theo từng commit với thời gian thực tế.

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
- Tìm kiếm lexical BM25 có chuẩn hóa dấu tiếng Việt; truy vấn không có từ khớp hoặc chỉ trùng một từ trong câu nhiều từ được loại. Chưa có embeddings/vector database, nên paraphrase không trùng từ có thể không tìm được nguồn. Trùng nhiều từ chưa chứng minh nguồn đủ trả lời; dịch vụ AI yêu cầu model báo thiếu bằng chứng và kiểm tra định dạng/ID đầu ra.
- Chọn context theo ngân sách JSON gồm cả metadata; nguồn quá dài được bỏ qua để xét đoạn ngắn hơn phía sau.
- Lịch sử chỉ dùng đúng bài học, giới hạn các lượt gần nhất và chủ đề cũ của người dùng. History là ngữ cảnh hội thoại, không phải bằng chứng kiến thức.
- Prompt tách sources/history/question thành dữ liệu JSON và yêu cầu dùng đúng citation ID. Đây là quy tắc prompt, không bảo đảm model chống được mọi prompt injection; dịch vụ AI kiểm tra đầu ra và ID trích dẫn nhưng không chứng minh tính đúng đắn của từng câu trả lời.

Nhận diện follow-up hiện là heuristic cho các cụm như “dễ hiểu hơn”, “giải thích lại”, “ví dụ”; chưa phải bộ phân loại ý định. Những câu hỏi vừa có cụm follow-up vừa chuyển chủ đề cần được kiểm tra thêm khi ghép dịch vụ.

## Phân công và các commit tiếp theo

- Người 1 giữ giao diện chính; demo riêng của AI có tại demo_server.py/demo_live.html.
- Người 2 giữ backend/router/database/auth. Người 3 chỉ bổ sung module này.
- Người 4 cung cấp văn bản/transcript từ PDF/OCR/audio; dịch vụ AI lõi nhận transcript. Demo có adapter ghép upload ghi âm với FileProcessingService, xem AUDIO_INTEGRATION.md.
- Người 5 giữ quiz/flashcard/progress.

Demo web đã ghép ghi âm; bước tiếp theo là kiểm thử ghép toàn bộ trong môi trường nhóm.

Nhánh backend/database hiện đề xuất AIProvider constructor không tham số, summarize(documents) và chat(question, documents, history). Commit 05 bổ sung BackendAIProvider tương thích trong module AI; xem INTEGRATION.md. Chưa sửa backend để ghép vào. Adapter ánh xạ chunk ID về document ID, chuyển history theo hợp đồng và giữ key phía server; backend vẫn phải xác thực dữ liệu được truyền vào.

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

Kiểm thử provider dùng phản hồi giả và tiến trình Python con để kiểm tra giới hạn output/timeout của transport. Không gọi API thật, không đọc file .env thật và không tiêu thụ quota. StudyAssistant phối hợp retrieval với provider và kiểm tra citation như mô tả bên dưới.

## Dịch vụ chat/Summary

```python
from ai_smart_context import StudyAssistant, MockProvider, Source, Turn

ai = StudyAssistant(MockProvider())  # offline; truyền GeminiProvider để gọi thật
sources = [Source('doc-1', 'lesson-1', 'SQLite', 'SQLite quản lý và truy vấn dữ liệu.')]
answer = ai.chat('lesson-1', 'SQLite là gì?', sources).to_dict()
followup = ai.chat('lesson-1', 'Giải thích dễ hiểu hơn', sources,
                  [Turn('user', 'SQLite là gì?', 'lesson-1')], mode='simple').to_dict()
summary = ai.summarize('lesson-1', sources).to_dict()
```

- ingest/chunking lọc theo lesson_id; chat chọn nguồn lexical BM25 rồi gửi nguồn và lịch sử có ngân sách. Các mode standard/simple/detailed được truyền vào prompt; cách diễn đạt phụ thuộc model. Mock chỉ trích xuất, không diễn giải theo mode.
- Không tìm được nguồn phù hợp hoặc follow-up thiếu câu hỏi trước: trả insufficient_context và không gọi provider. Khi provider báo thiếu bằng chứng cũng trả insufficient_context.
- Phản hồi ok phải có nội dung đúng kiểu và citation thuộc chính context của lần gọi. Dịch vụ bỏ citation trùng, ánh xạ về chunk/source/title/excerpt/timestamp thật từ nguồn. Citation do model gửi không được tự tạo timestamp. Citation hợp lệ chỉ xác minh ID; không chứng minh model suy luận chính xác hoặc mọi câu đều được nguồn hỗ trợ.
- Summary xử lý tất cả chunk theo các batch, kiểm tra từng kết quả rồi tổng hợp bản tóm tắt trung gian theo ngân sách JSON. Không bỏ qua phần thất bại hoặc âm thầm cắt nguồn để báo thành công. covered_chunks là số chunk đã đưa vào các batch, không bảo đảm bản tóm tắt nêu mọi chi tiết. Tài liệu dài có nhiều lượt gọi và có thể tốn quota; provider_calls là số lần gọi generate, không gồm retry HTTP nội bộ.
- ProviderError truyền cho backend/bên gọi xử lý; dịch vụ không tự đổi provider, không cache và không lưu lịch sử. Kiểm tra quyền truy cập vẫn thuộc backend. Mỗi request phải cung cấp sources/history đã được xác thực cho đúng người dùng.
- Transcript được đưa vào bằng Source(kind='transcript', text=...) hoặc segments có timestamp thật. Đọc file ghi âm/nhận dạng giọng nói thuộc người phụ trách xử lý file; commit này chỉ xử lý dữ liệu transcript đã có.

Adapter theo hợp đồng backend/database đã có ở backend_adapter.py; hướng dẫn ghép tại INTEGRATION.md. Demo web có tại demo_server.py; hướng dẫn ghi âm tại AUDIO_INTEGRATION.md. Module không sửa router, database, auth hoặc giao diện chung của nhóm.
