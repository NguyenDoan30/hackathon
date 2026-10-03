# Kế hoạch kết nối FE với API thật

FE được bàn giao trên nhánh riêng, trong frontend/**, theo yêu cầu của người dùng. Hiện dùng fixtures và localStorage; kết nối backend thật chưa thực hiện. Không chuyển hồ sơ demo hay ID mẫu sang backend thật.

## Ranh giới khi 5 người cùng làm

Mã FE dự kiến chỉ nằm trong `frontend/**`: giao diện, kiểu dữ liệu, adapter API, cấu hình và dependency/lockfile riêng của FE. Tài liệu bàn giao nằm cùng thư mục frontend. Không sửa backend, database, AI/RAG, xử lý PDF/OCR/STT hoặc logic learning của thành viên khác. Trước tích hợp, xác định nhánh đích và danh sách file thay đổi; dùng nhánh FE riêng và tránh các file cấu hình ở gốc repo nếu nhóm chưa thống nhất.

| Phụ trách | FE kết nối |
|---|---|
| Người 2 — Backend/API/database | Phiên đăng nhập, CRUD bài học, upload/status và endpoint công cụ học |
| Người 3 — AI/Summary/Tutor/RAG | Hiển thị tóm tắt, câu trả lời và nguồn do API trả về |
| Người 4 — PDF/OCR/STT | Gửi tệp và hiển thị tiến trình, transcript, lỗi xử lý |
| Người 5 — Flashcard/Quiz/Progress | Hiển thị thẻ; gửi review/bài làm; hiển thị điểm và tiến độ |

Các thay đổi cần ở module khác được ghi thành yêu cầu cho đúng người phụ trách. FE không tự cài AI, OCR, STT, chấm điểm thật hoặc thuật toán lịch ôn.

## Hợp đồng tham chiếu

Nguồn: [API_CONTRACT.md — nhánh backend/database-stepwise](https://github.com/NguyenDoan30/hackathon/blob/backend/database-stepwise/backend/docs/API_CONTRACT.md), phiên bản 1.0.0, đang thuộc [draft PR #2](https://github.com/NguyenDoan30/hackathon/pull/2). Đây là hợp đồng đang review; cần chốt lại với người 2 trước khi triển khai. Dùng Swagger `/docs` và OpenAPI `/openapi.json` của backend chạy thực tế để đối chiếu đầy đủ response.

Base URL tích hợp mặc định: `http://127.0.0.1:8000`; không tự thêm `/api` hoặc `/api/v1`. Backend demo có thể chạy cổng 8765 theo hợp đồng. CORS phải cho phép origin FE `http://127.0.0.1:3100` hoặc origin thực tế được nhóm chọn. Thiết lập URL trong cấu hình FE khi tích hợp; không nhúng token hay secret vào mã nguồn.

| Chức năng | API và yêu cầu adapter FE |
|---|---|
| Đăng ký/đăng nhập | `POST /auth/register {name,email,password}`, `POST /auth/login {email,password}`; session có `access_token`, `token_type`, `expires_at`, `user`. Register thật yêu cầu mật khẩu 10–128 ký tự; form demo hiện chỉ kiểm tra tối thiểu 6 ký tự. |
| Phiên | `GET /auth/me`, `POST /auth/logout` → 204. Token opaque được gửi bằng `Authorization: Bearer <access_token>`; không giải mã như JWT hoặc tự chọn `user_id`. |
| Bài học | `GET /lessons?q=&limit=&offset=`, `POST /lessons {title,description}`, `GET /lessons/{lesson_id}`; PATCH/DELETE cùng đường dẫn. ID UUID; field như `created_at` cần map sang kiểu UI. Backend chưa có `topic`, `accent` và cấu trúc progress giống demo. |
| Upload | `POST /upload` với multipart `lesson_id` + `file` → **202**, trả `DocumentPublic`. Không tự đặt `Content-Type` cho FormData; upload nhiều tệp gửi từng request theo hợp đồng. |
| Trạng thái tài liệu | `GET /documents/{document_id}`; `pending → processing → ready/failed`. Poll có giới hạn và dừng khi rời trang; 202 chỉ xác nhận nhận tệp. Hiển thị `error_code`, dùng `POST /documents/{id}/retry` khi failed. Download cần Bearer qua `/documents/{id}/download`; DELETE xóa tài liệu. |
| Summary | `GET /summary/{lesson_id}` để lấy bản lưu, `POST /summary/{lesson_id}/generate` để sinh; cần tài liệu ready. Map response thực tế sang overview/keyPoints/takeaways của UI, không giả định schema giống fixtures. |
| Tutor | `POST /chat {lesson_id,question}`, `GET /chat/{lesson_id}?limit=&offset=`. Response nguồn là ID tài liệu; map sang tên từ danh sách tài liệu. API chưa nhận `tutorMode`, chưa có streaming/context endpoint riêng. |
| Flashcard | `GET /flashcards/{lesson_id}` → `{items}`; `POST /flashcards/{lesson_id}/generate`; `POST /flashcards/{flashcard_id}/review {rating}` với `again/hard/good/easy`. Map ID/schema từ backend; không dùng ID thẻ mẫu. |
| Quiz | `GET /quiz/{lesson_id}`, `POST /quiz/{lesson_id}/generate`; `POST /quizzes/{quiz_id}/submit {answers:{question_id:"option text"}}`. Câu hỏi nhận trước không có answer/explanation; chỉ lấy điểm, đáp án và giải thích từ kết quả submit. |
| Tiến độ | `GET /progress`, `GET /progress/{lesson_id}`. Hiển thị số liệu backend cung cấp; không dùng lịch sử quiz localStorage làm dữ liệu thật. |

Lessons/chat có phân trang `{items,total,limit,offset}`; flashcards là `{items}`, quiz là object của quiz mới nhất. Backend dùng snake_case, timestamps UTC ISO-8601. `source_mode` trong hợp đồng là **`demo` / `production`**, trong kiểu UI demo hiện là `demo` / `live`; adapter cần map rõ hoặc đổi kiểu FE khi tích hợp. Kết quả có `source_mode=demo` luôn phải có nhãn dữ liệu mẫu dù đã đi qua backend.

## Chế độ API thật và lỗi

Tạo lớp kết nối riêng trong FE để xử lý base URL, Bearer, phân trang, mapping response và hủy request. Lựa chọn Demo/API thật phải rõ ràng; **không tự fallback sang fixtures khi API lỗi**, đặc biệt ở login, upload hoặc submit quiz. Đổi chế độ phải tách dữ liệu và ID của mỗi nguồn.

API trả lỗi dạng `{error:{code,message},request_id}`. Hiển thị lỗi hữu ích và hành động thử lại phù hợp; 401 yêu cầu đăng nhập lại, 404 hiển thị nội dung chưa tồn tại, 409 xử lý ngữ cảnh chưa ready, 413/415/422 xử lý tệp hoặc dữ liệu không hợp lệ, 502/503 hiển thị provider đang lỗi/chưa sẵn sàng. Không coi upload là thành công xử lý trước khi tài liệu đạt ready. Giữ request ID để hỗ trợ đối chiếu lỗi; không hiển thị exception nội bộ hoặc mật khẩu.

## Các điểm chưa có API

Mindmap, tùy chọn mức giải thích Tutor, streaming, lưu sổ tay cá nhân, lịch ôn tự động và phân tích chủ đề mạnh/yếu chưa có endpoint trong hợp đồng này. Trong demo chúng chỉ dùng nội dung mẫu hoặc lưu cục bộ theo nhãn hiện có. Chỉ nối khi người phụ trách xác nhận hợp đồng; chưa có API thì giao diện phải nói rõ.

Ghi âm dùng microphone trên trình duyệt khi người dùng bấm bắt đầu và cấp quyền. Byte ghi âm chỉ ở phiên hiện tại; cần gửi tệp audio qua `/upload` trong giai đoạn tích hợp. Hiện chưa có STT thực tế. Ghi chú được nhập như văn bản cũng cần thống nhất cách gửi với backend trước khi coi là nguồn tài liệu thật.

## Kiểm tra trước bàn giao tích hợp

Khi triển khai kết nối API thật: đối chiếu schema/OpenAPI; kiểm tra đăng nhập/logout/401, tạo bài, upload và poll đến ready/failed/retry, Summary, Tutor, review, quiz submit, progress; xác nhận lỗi API không trở thành dữ liệu mẫu. Chạy `npm run typecheck` và `npm run build`, thử bố cục desktop/mobile và thao tác bàn phím. Ghi lại kết quả thực tế cùng giới hạn còn lại; tài liệu này chưa xác nhận các kiểm tra đã đạt.
