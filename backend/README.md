# AI Study Assistant — Backend / Database (Người 2)

Backend FastAPI + SQLite cho dự án AI Study Assistant của nhóm 5 người. Toàn bộ phần Backend / Database nằm trong `backend/`, đã được đưa lên nhánh `main` và giữ ranh giới rõ với `frontend/`, `ai_smart_context/`, `file_processing/` và `learning/` để các thành viên có thể phát triển song song.

## Chạy nhanh trên Windows

Yêu cầu Python **3.12**. Trên máy đã được chuẩn bị, môi trường `.venv` đang có sẵn; chạy:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\run-demo.ps1
```

Mở `http://127.0.0.1:8765/demo`. Swagger: `http://127.0.0.1:8765/docs`.

Trên máy mới, tạo môi trường riêng trước:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
powershell -ExecutionPolicy Bypass -File .\run-demo.ps1
```

Linux/macOS: `python3.12 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.lock.txt`, rồi `APP_MODE=demo DATA_DIR=./data/demo .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765`.

`requirements.txt` là các dependency trực tiếp; `requirements.lock.txt` ghi phiên bản đã kiểm thử. Không cần Node, framework frontend hoặc API key để xem demo. Dùng một process Uvicorn, không thêm `--workers` cho bản MVP này.

## Demo thể hiện điều gì?

Trang riêng nằm trong `app/demo/`, không sử dụng thư mục frontend của Người 1. UI có tổng quan, thư viện, tạo/sửa/xóa bài học, upload, xem/tải/xóa tài liệu, summary, chat, flashcard, quiz, tiến độ, API Console và sơ đồ database. Không dùng CDN/font ngoài; trang demo chạy bằng HTML/CSS/JS local.

API, xác thực, database, upload, lưu/đọc dữ liệu và quyền truy cập đều hoạt động thật. AI, trích xuất PDF/ảnh/audio, sinh câu hỏi và chấm quiz dùng fixture trong `app/integrations/demo.py`. Fixture OOP cố định chỉ chứng minh giao diện kết nối; không thể đánh giá chất lượng AI hoặc độ chính xác OCR từ demo.

Tài khoản mẫu chỉ được tạo khi `APP_MODE=demo`:

- Email: `demo@studyassistant.dev`
- Mật khẩu: `DemoStudy!2026`
- UI tự đăng nhập tài khoản này, token lưu trong sessionStorage.
- Database demo: `data/demo/study.db`; file upload: `data/demo/uploads/`.

Lần đầu khởi động tạo hai bài học mẫu; một bài có tài liệu OOP, summary, flashcard, quiz và một bài làm mô phỏng. Những lần sau giữ nguyên dữ liệu. Nếu xóa tài khoản/bài học mẫu, không tự tạo lại toàn bộ dữ liệu trên mỗi request.

## Kịch bản xem sản phẩm (3–5 phút)

1. Mở tổng quan: xem API và các số liệu đọc thật từ database.
2. Vào thư viện → tạo bài học mới → upload Markdown mẫu.
3. Xem tài liệu đã xử lý; tải xuống để đối chiếu file gốc.
4. Tạo summary, hỏi AI Tutor; quan sát nhãn mô phỏng và dữ liệu đã lưu.
5. Tạo flashcard → mở đáp án → lưu đánh giá độ nhớ.
6. Tạo quiz → trả lời đủ câu hỏi → nộp bài → xem điểm và tiến độ.
7. Vào API Console gửi GET /lessons; chọn một request để xem JSON.
8. Dừng server bằng Ctrl+C rồi chạy lại: bài học, tài liệu, chat và kết quả vẫn còn.

## Chạy với module thật

```powershell
Copy-Item .env.example .env
# Điền các provider của đồng đội trong .env.
powershell -ExecutionPolicy Bypass -File .\run-api.ps1
```

API ở `http://127.0.0.1:8000`, Swagger ở `/docs`. Script chọn `APP_MODE=production` và `data/production/` để tách khỏi demo. Chế độ này tắt trang demo, không seed tài khoản và không chọn fixture mặc định. Module chưa cấu hình trả lỗi `PROVIDER_UNAVAILABLE`; file xử lý thất bại có thể thử lại.

Đây là chế độ **tích hợp thật của MVP local**. Job upload chạy trong process; chưa có hàng đợi bền vững hoặc hạ tầng triển khai nhiều server. Khi server bị dừng giữa lúc xử lý, tài liệu dở dang được đánh dấu `PROCESSING_INTERRUPTED` và cần gọi retry. Module đồng đội phải đặt timeout cho các lời gọi dịch vụ bên ngoài.

## Cấu trúc và ranh giới

| Vị trí | Chức năng |
|---|---|
| `app/main.py` | App factory, middleware, xử lý lỗi, CORS, health |
| `app/api/` | Auth, lessons, upload/document, AI/learning API |
| `app/models/` | Response models công khai cho Swagger |
| `app/schemas/` | Input và output contract của provider |
| `app/database.py` | SQLite session, transaction, migration |
| `app/security.py` | Hash mật khẩu, phiên đăng nhập, quyền sở hữu |
| `app/services/` | Điều phối, xử lý nền, lưu kết quả, seed demo |
| `app/integrations/` | Protocol, nạp provider và fixture riêng của demo |
| `app/demo/` | Giao diện kiểm tra backend riêng |
| `migrations/` | SQL schema có phiên bản |
| `tests/` | Kiểm thử backend và giao diện kết nối |
| `docs/` | Đặc tả API, tích hợp, OpenAPI và kết quả kiểm tra |

Người 3 viết AI/RAG; Người 4 viết file processing; Người 5 viết learning/scoring. Backend nhận output, kiểm tra cấu trúc và lưu database. Người 1 có thể dùng frontend Next.js hoặc Flutter vì API dùng HTTP/JSON tiêu chuẩn.

## Database và xử lý dữ liệu

SQLite chuẩn của Python, SQL tham số hóa, khóa ngoại, WAL, busy_timeout 10 giây và transaction. Migration tự áp dụng khi startup, ghi vào `schema_migrations`; không dùng ORM và không gọi create_all để thay migration.

Các bảng: users, sessions, lessons, documents, transcripts, summaries, chats, flashcards, flashcard_reviews, quizzes, quiz_attempts, schema_migrations. Mật khẩu dùng Argon2; database chỉ lưu hash token phiên, có thời hạn và logout thu hồi được. Dữ liệu truy cập luôn được kiểm tra theo chủ bài học. ID ngoài tài khoản trả 404.

Upload hỗ trợ `.pdf`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.mp3`, `.wav`, `.m4a`, `.ogg`; mặc định tối đa 20 MB/file. Kiểm tra đuôi file và chữ ký định dạng cơ bản; TXT/MD phải là UTF-8, không rỗng. Đây không phải parser xác thực toàn bộ file; module Người 4 chịu trách nhiệm đọc và xác minh định dạng sâu hơn. Tên lưu do server tạo, không dùng đường dẫn do người dùng gửi. Nội dung trùng trong cùng bài học trả 409.

Quiz GET không trả đáp án đúng hoặc lời giải. POST submit yêu cầu đủ câu hỏi, option hợp lệ; module Người 5 chấm bài, backend kiểm tra tổng/điểm nhất quán rồi lưu. Quiz mới giữ lại phiên bản cũ và bài làm cũ. Tạo lại flashcard thay bộ hiện tại và xóa các review gắn với bộ đó. Thay đổi tài liệu không tự sinh lại nội dung AI; người dùng gọi generate khi cần cập nhật.

Xóa bài học xóa dữ liệu phụ qua khóa ngoại và file đã lưu. Xóa tài liệu xóa transcript liên quan; các nội dung học đã sinh vẫn giữ lại cho đến khi được tạo lại hoặc xóa bài học.

## Phối hợp Git

- Chỉ đưa thư mục `backend/` vào nhánh dành cho backend khi được duyệt.
- Không sửa README chung, frontend, AI, file processing hoặc learning của người khác.
- Thống nhất `docs/API_CONTRACT.md` và `docs/INTEGRATION.md` trước khi ghép.
- Mỗi người dùng SQLite local riêng. Không dùng chung file database qua ổ mạng hoặc dịch vụ đồng bộ.
- `.gitignore` riêng đã loại `.venv`, `.env`, database, uploads/data và dữ liệu test.
- Kiểm tra lại main trước khi đưa thay đổi vào repo vì các thành viên có thể đang làm đồng thời.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Bao gồm workflow, quyền truy cập chéo tài khoản, thu hồi/hết hạn phiên, file sai/rỗng/quá lớn/trùng, output provider không hợp lệ, quiz không lộ đáp án, rollback, cascade và file cleanup, lưu dữ liệu sau restart, migration lặp lại, CORS, nhiều request ghi đồng thời và production không dùng fallback demo. Test dùng database riêng, không xóa database demo.

Tài liệu chi tiết: `docs/API_CONTRACT.md`, `docs/INTEGRATION.md`, `docs/openapi.json`, `docs/VALIDATION.md`.

Tham chiếu kỹ thuật chính thức: [FastAPI](https://fastapi.tiangolo.com/tutorial/), [SQLite WAL](https://www.sqlite.org/wal.html).
