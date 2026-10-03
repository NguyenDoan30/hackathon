# Kết quả kiểm tra — 03/10/2026 (Asia/Saigon)

## Backend

37 test case đạt. Lần kiểm tra cuối sau khi thêm các response model: **37 passed**. Runtime local Python 3.12.15; dependency cụ thể được ghi trong requirements.lock.txt.

Kiểm tra được: workflow upload/summary/chat/learning/progress; hash mật khẩu và token; logout/hết hạn phiên; xác thực dữ liệu; API không phản hồi lại mật khẩu; quyền truy cập chéo tài khoản ở endpoint bài học, tài liệu, upload, chat, learning và tiến độ; file sai/rỗng/quá lớn/trùng và đường dẫn an toàn; output module không hợp lệ không ghi dữ liệu; production không seed/fallback fixture; CORS; cascade xóa dữ liệu/file; migration chạy lại; dữ liệu sau restart; 15 request tạo bài học với 5 thread cùng lúc.

Có một cảnh báo deprecation từ Starlette TestClient về backend httpx của công cụ kiểm thử. Test vẫn chạy và đạt; không ảnh hưởng API runtime của demo. Không đổi dependency test sang một thư viện chưa kiểm chứng chỉ để giấu cảnh báo.

## Kiểm tra trực tiếp giao diện

Thao tác qua browser trên trang local:

1. Tạo bài học mới bằng form, xác nhận trang chi tiết.
2. Upload Markdown mẫu bằng UI, xác nhận tài liệu xuất hiện và được xử lý.
3. Tạo summary, hiển thị nội dung và nhãn mô phỏng.
4. Gửi câu hỏi AI Tutor, xác nhận phản hồi và lưu lịch sử.
5. Tạo bộ flashcard, kiểm tra câu hỏi hiển thị.
6. Tạo quiz, chọn ba đáp án, nộp bài.
7. Xem tiến độ: **3/3 câu đúng, 100%, 1 bài làm** cho bài học kiểm tra.
8. Gửi GET /health qua API Console, xác nhận HTTP 200 và database connected; nhật ký request cập nhật đúng.

Không có lỗi JavaScript ghi nhận khi kiểm tra thao tác. Trang có CSS thích ứng màn hình hẹp và tôn trọng prefers-reduced-motion; không tải font/CDN ngoài. Đã sửa và kiểm tra lại icon điều hướng khi nút chờ xử lý và ID ổn định của từng dòng nhật ký. Ảnh xem trước: demo-cover.jpg và demo-preview.jpg trong docs/.

## Phạm vi kết luận

Đã kiểm thử phần backend/database và fixture của giao diện kết nối. Chưa kiểm thử độ chính xác AI/RAG, OCR/STT hoặc thuật toán learning thật vì code của các thành viên này chưa có trong snapshot repo. Chưa thực hiện test tích hợp toàn hệ thống với frontend sản phẩm. Kết quả đồng thời chỉ chứng minh workload local nêu trên, không phải benchmark tải production.

Snapshot repo ban đầu: `6bcf8527529136e4989ed403cb6bd8d218b33bc5`. Không có commit/push/PR hoặc thay đổi dữ liệu GitHub trong giai đoạn này.
