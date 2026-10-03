# Kiểm tra FE — 2026-10-03

Môi trường: Windows, Node.js 24.19.0, npm 10.9.3, Next.js 15.5.27.

Đã đạt:

- Cài dependency từ lockfile bằng npm ci.
- TypeScript strict: tsc --noEmit.
- tests/demo.test.cjs: snapshot độc lập, lưu/đọc, dữ liệu hỏng, localStorage bị chặn, không lưu mật khẩu, fixture độc lập, quiz đúng/sai/thiếu đáp án, nhãn Tutor và nguồn mẫu.
- Build preview: 24 modules, khoảng 2016 KB JavaScript và 66 KB CSS.
- Trình duyệt: trang chủ có ba bài mẫu, mở bài cơ sở dữ liệu, xem tóm tắt, chuyển Tutor và nhận phản hồi có nhãn mẫu.

Giới hạn:

- Build Next.js biên dịch thành công nhưng không hoàn tất: tiến trình worker bị Windows chặn với spawn EPERM. Thử worker threads vượt qua kiểm tra kiểu nhưng gặp DataCloneError ở bước sinh trang. Cấu hình cuối giữ worker mặc định; cần chạy lại npm run build trên máy/CI cho phép tiến trình con trước khi triển khai production.
- Chưa xác nhận toàn bộ responsive, microphone, upload hoặc luồng end-to-end với backend thật. Bản này là frontend demo độc lập, không xác nhận khả năng AI/STT thật.
