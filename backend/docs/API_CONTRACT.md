# Đặc tả API — Người 2

Version 1.0.0. URL local tích hợp mặc định `http://127.0.0.1:8000`. Demo local dùng port 8765. Swagger ở `/docs`, schema máy đọc ở `/openapi.json`. Giữ nguyên các endpoint chính của bảng phân công, không tự thêm prefix `/api/v1`.

## Quy ước

JSON request/response, trừ upload multipart và download file. Tất cả endpoint dữ liệu yêu cầu `Authorization: Bearer <access_token>`. `/health`, `/auth/register`, `/auth/login` không cần token. Token là opaque session token, không phải JWT. Không gửi `user_id` để chọn người dùng; backend lấy từ phiên. UUID string là ID, timestamps UTC ISO-8601.

Danh sách lessons/chat trả `{items,total,limit,offset}`. GET flashcards trả `{items}`; GET quiz trả quiz mới nhất. Flashcard list tối đa 50 thẻ do provider; quiz tối đa 50 câu. Lesson list `limit=1..100`, chat `limit=1..100`, `offset>=0`; UI demo hiển thị tối đa 100 bài học.

Mọi request có `X-Request-ID` và `X-Process-Time` (thời gian server). Frontend có thể đọc nhờ CORS expose_headers. CORS được cấu hình qua `.env`, không cho phép mọi origin mặc định.

## Endpoint

| Method | URL | Input / behavior | Thành công |
|---|---|---|---|
| GET | /health | Trạng thái và provider | 200 HealthPublic |
| POST | /auth/register | name, email, password (10–128 ký tự) | 201 SessionPublic |
| POST | /auth/login | email, password | 200 SessionPublic |
| GET | /auth/me | Tài khoản hiện tại | 200 UserPublic |
| POST | /auth/logout | Thu hồi phiên hiện tại | 204 |
| POST | /lessons | title (1–160), description (0–2000) | 201 LessonPublic |
| GET | /lessons | q, limit=20, offset=0 | 200 LessonPage |
| GET | /lessons/{lesson_id} | Bài học + tài liệu + transcript + progress | 200 LessonDetail |
| PATCH | /lessons/{lesson_id} | title và/hoặc description; không truyền null | 200 LessonPublic |
| DELETE | /lessons/{lesson_id} | Xóa cả dữ liệu liên quan và file | 204 |
| POST | /upload | multipart: lesson_id, file | 202 DocumentPublic |
| GET | /documents/{document_id} | Trạng thái và content | 200 DocumentPublic |
| GET | /documents/{document_id}/download | File gốc; cần Authorization | 200 binary |
| POST | /documents/{document_id}/retry | Chỉ tài liệu failed | 202 DocumentPublic |
| DELETE | /documents/{document_id} | Xóa tài liệu, transcript, file | 204 |
| POST | /summary/{lesson_id}/generate | Gọi AI; cần tài liệu ready | 200 SummaryPublic |
| GET | /summary/{lesson_id} | Tóm tắt đã lưu | 200 SummaryPublic |
| POST | /chat | lesson_id, question (1–4000) | 201 ChatPublic |
| GET | /chat/{lesson_id} | limit=50, offset=0; thời gian tăng dần | 200 ChatPage |
| POST | /flashcards/{lesson_id}/generate | Gọi learning, thay bộ thẻ | 201 CardPage |
| GET | /flashcards/{lesson_id} | Bộ thẻ hiện tại | 200 CardPage |
| POST | /flashcards/{flashcard_id}/review | rating: again/hard/good/easy | 201 ReviewPublic |
| POST | /quiz/{lesson_id}/generate | Gọi learning, lưu phiên bản mới | 201 QuizPublic |
| GET | /quiz/{lesson_id} | Quiz mới nhất, không có answer/explanation | 200 QuizPublic |
| POST | /quizzes/{quiz_id}/submit | answers: map question_id → option text | 201 AttemptPublic |
| GET | /progress | Tổng hợp quiz/review của tài khoản | 200 ProgressPublic |
| GET | /progress/{lesson_id} | Tiến độ và 10 bài làm gần nhất | 200 ProgressPublic |

Định nghĩa đầy đủ từng response có trong Swagger/OpenAPI và `app/models/__init__.py`.

## Ví dụ frontend

```javascript
const root = 'http://127.0.0.1:8000';
const login = await fetch(root + '/auth/login', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'you@example.com', password: 'your-password'})
});
if (!login.ok) throw new Error((await login.json()).error.message);
const session = await login.json();
const headers = {Authorization: `Bearer ${session.access_token}`};
const response = await fetch(root + '/lessons', {headers});
const lessons = await response.json();

const form = new FormData();
form.append('lesson_id', lessons.items[0].id);
form.append('file', selectedFile);
const uploaded = await fetch(root + '/upload', {method:'POST',headers,body:form});
// Không set Content-Type bằng tay cho FormData.
```

Upload trả 202 = đã nhận file, chưa khẳng định xử lý thành công. Poll GET document đến `ready` hoặc `failed`, ví dụ mỗi giây; dừng poll khi người dùng rời trang. Luồng status: pending → processing → ready/failed. Khi failed, hiển thị error_code và nút retry. Trong demo, các fixture chạy nhanh nên GET đầu tiên có thể đã ready.

Chat:

```json
{"lesson_id":"<lesson-uuid>","question":"Giải thích đa hình bằng ví dụ đơn giản"}
```

Quiz submit (các key phải đúng ID câu hỏi trả về):

```json
{"answers":{"q1":"Một thể hiện của class","q2":"Đóng gói","q3":"Đa hình"}}
```

`source_mode=demo` chỉ kết quả mô phỏng; `production` là kết quả qua provider được cấu hình. Không suy ra rằng output production luôn chính xác; chất lượng nội dung thuộc module provider.

## Lỗi

```json
{
  "error":{"code":"CONTEXT_NOT_READY","message":"Cần ít nhất một tài liệu đã xử lý để thực hiện chức năng này."},
  "request_id":"<request-uuid>"
}
```

| HTTP | Các code điển hình |
|---|---|
| 401 | AUTH_REQUIRED, SESSION_INVALID, LOGIN_FAILED |
| 404 | LESSON_NOT_FOUND, DOCUMENT_NOT_FOUND, SUMMARY_NOT_FOUND, QUIZ_NOT_FOUND |
| 409 | EMAIL_EXISTS, DOCUMENT_EXISTS, CONTEXT_NOT_READY, DOCUMENT_NOT_FAILED, QUIZ_MODE_MISMATCH |
| 413 | FILE_TOO_LARGE |
| 415 | UNSUPPORTED_FILE, FILE_CONTENT_MISMATCH |
| 422 | VALIDATION_ERROR, EMPTY_FILE, INVALID_FILENAME, INVALID_ANSWERS |
| 502 | PROVIDER_FAILED, PROVIDER_INVALID_OUTPUT |
| 503 | PROVIDER_UNAVAILABLE |

Validation details chỉ chứa field/message/type, không trả lại input mật khẩu. Không hiển thị exception nội bộ cho người dùng. Các lỗi xử lý nền được ghi trong Document.error_code, không thể đổi mã HTTP của upload đã nhận trước đó.
