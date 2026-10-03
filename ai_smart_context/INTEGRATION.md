# Ghép AI với backend của nhóm

Adapter: `ai_smart_context.backend_adapter:BackendAIProvider`. Constructor không cần tham số; có hai phương thức đồng bộ `chat(question, documents, history)` và `summarize(documents)`. Không cần đưa code AI vào thư mục backend hoặc sửa router.

## Hợp đồng đã kiểm tra

- `backend/database` tại `37903d5e828823f06e0d105ca358675ecdf3a46b`.
- `backend/database-stepwise` tại `221c1532d2bf82b42fbc420bbbd1b2fe49654296`.
- Input documents: danh sách `{id, filename, content}` đã ready, được backend lọc theo quyền và đúng bài học.
- Input history: tối đa 12 cặp `{question, answer}`, thứ tự cũ → mới, cùng bài học.
- Output chat: đúng hai trường `{answer, sources}`; sources là ID tài liệu, không phải ID chunk.
- Output Summary: đúng hai trường `{summary, key_points}`.

`ProviderError` truyền ra bên gọi. Backend hiện bắt lỗi này thành HTTP 502 `PROVIDER_FAILED`; metadata retry/quota chưa được truyền tới frontend qua backend nhóm. Adapter không đổi lỗi quota thành câu trả lời thành công hoặc tự chuyển sang mock. Summary thiếu bằng chứng phát sinh `ProviderError('insufficient_context', ...)` để backend không lưu thông báo thất bại thành bản tóm tắt. Chat thiếu bằng chứng trả thông báo và sources rỗng theo hợp đồng hiện tại.

## Cấu hình khi người phụ trách backend ghép

Các bước sau là hướng dẫn, chưa tự sửa `.env` hoặc file của người khác. Backend phải chạy Python >=3.10 và import được module AI, bằng repo root trong PYTHONPATH hoặc môi trường cài đặt tương đương. AI chỉ dùng thư viện chuẩn; các dependency FastAPI/Pydantic/auth thuộc backend.

Trong cấu hình local của backend, chọn:

```dotenv
APP_MODE=production
AI_PROVIDER=ai_smart_context.backend_adapter:BackendAIProvider
GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_TRANSPORT=curl
```

Điền key/model thật chỉ ở máy backend. Đây là ví dụ cấu hình; không commit key. Backend hiện gọi load_dotenv trước khi nạp provider; adapter đọc môi trường process và không tự đọc `.env` của module AI. Giữ cấu hình FILE_PROVIDER/LEARNING_PROVIDER của các thành viên khác theo bản ghép riêng.

Có thể chọn GEMINI_TRANSPORT=urllib; curl cần được cài trên máy và hỗ trợ `%header{retry-after}`. TLS verification luôn bật. Tên model phải là model tài khoản hỗ trợ. Thiếu key/model hoặc transport sai sẽ làm việc khởi tạo provider thất bại, không dùng mock thay thế.

Ví dụ thêm repo root vào phiên PowerShell đang chạy backend (đổi đường dẫn cho đúng máy):

```powershell
$env:PYTHONPATH = 'C:\path\to\hackathon'
```

Khởi động lại backend bằng launcher của người phụ trách backend sau khi cấu hình. `APP_MODE=demo` hiện chọn DemoAI riêng của backend và không dùng adapter này; kiểm tra ghép thật phải dùng production. Commit adapter không tự khởi động server hay gửi tài liệu tới Google.

## Kiểm tra offline trong module AI

Từ repo root:

```powershell
python -m unittest discover -s ai_smart_context/tests
python -m ai_smart_context.examples.backend_adapter_demo
```

Ví dụ gọi dùng MockProvider được truyền rõ ràng, không đọc key hoặc gọi Google. Kết quả mô phỏng có nhãn trong nội dung. BackendAIProvider() không tham số luôn tạo GeminiProvider; không có lựa chọn mock ngầm trong biến môi trường.

## Giới hạn cần thống nhất khi ghép

- Hợp đồng không có lesson_id. Adapter dùng nhãn nội bộ cho từng lần gọi và không lưu nguồn/lịch sử giữa các lần gọi. Nhãn này không thay thế kiểm tra quyền; backend phải truyền đúng dữ liệu. Không có cache dùng chung.
- Tối đa 100 tài liệu, ID tối đa 200 ký tự, filename tối đa 500 ký tự, content không rỗng tối đa 1 triệu ký tự/tài liệu, tổng nguồn tối đa 2 triệu ký tự. Trùng ID hoặc vượt giới hạn bị từ chối trước khi gọi AI.
- History question tối đa 4.000 ký tự, answer tối đa 100.000 ký tự theo backend. Mỗi answer lịch sử chỉ giữ 20.000 ký tự đầu để chuyển sang Turn, rồi history_context chọn theo ngân sách 2.200 ký tự mặc định. Không âm thầm cắt nội dung tài liệu; history có cắt theo giới hạn đã công bố.
- API này chỉ chuyển text transcript đã trích xuất trong content. Không nhận file audio, không thực hiện STT và không tự tạo timestamp. Backend hiện không truyền segments/timestamp, nên output của adapter không có mốc ghi âm. API StudyAssistant trực tiếp vẫn hỗ trợ segments thật.
- Sources trả về chỉ chứa document ID đã được kiểm tra. Backend AnswerResult không nhận excerpt/timestamp/status/provider/context của Result, nên adapter bỏ các trường đó để tránh lỗi extra='forbid'. SummaryResult cũng không có examples hoặc citations.
- Settings mặc định: timeout 30 giây mỗi lần gọi, retry hữu hạn. Summary dài có thể gọi provider nhiều lần. Không có bộ điều phối quota giữa request, tổng deadline, hàng đợi hoặc streaming.
- Kiểm thử loader/schema offline không thay thế kiểm tra API HTTP, quyền truy cập, file processing và Gemini thật trong môi trường ghép của nhóm.
