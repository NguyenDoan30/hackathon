# Luma — AI Study Assistant frontend

Frontend demo độc lập, dùng Next.js, React và TypeScript. Tất cả mã nằm trong `frontend/` để nhóm có thể review và ghép riêng với backend.

## Chạy Next.js

Cần Node.js 20.9 trở lên và npm. Từ thư mục repo:

```sh
cd frontend
npm ci
npm run dev
```

Mở http://127.0.0.1:3100. Build production bằng `npm run build`, sau đó `npm start`.

## Chạy bản preview độc lập

Cần thêm Python 3. Từ thư mục `frontend` sau khi chạy `npm ci`:

```sh
npm run build:preview
python start-demo.py --port 3101
```

Mở http://127.0.0.1:3101. Giữ cửa sổ server mở; Ctrl+C để dừng. Các tệp `demo/app.js`, `demo/app.css`, `demo/index.html` được tạo lại từ source, không đưa vào Git.

## Phạm vi hiện tại

- Giao diện thư viện, bài học, tóm tắt, Tutor, sơ đồ, flashcard, quiz, sổ tay và tiến độ.
- Ba bài mẫu và dữ liệu mẫu cho bài mới; lưu trạng thái bằng localStorage trên trình duyệt.
- Chọn tài liệu và giao diện ghi âm phục vụ trải nghiệm demo. Chưa gửi file đến backend, chưa chuyển audio thành văn bản trong FE này.
- Tutor, summary và quiz sử dụng fixtures; không gọi Gemini. Đăng nhập demo không phải xác thực thật và không lưu mật khẩu.

Module AI thật trên nhánh khác cần được nối qua API trong bước tích hợp. Không đặt API key vào mã trình duyệt. Xem `FE_INTEGRATION.md` để tham khảo ranh giới và API cần đối chiếu lại.

## Cấu trúc

- `app/`: layout, CSS toàn cục và route.
- `components/`: UI từ bộ file bàn giao.
- `types.ts`, `services/`: kiểu dữ liệu, fixtures và lưu trữ demo được bổ sung.
- `scripts/`: đóng gói preview và điều hướng cho preview.
- `tests/`: kiểm thử dữ liệu, lưu trữ, Tutor mẫu và chấm quiz mẫu.

Chạy `npm run typecheck`, `npm test`, `npm run build:preview`. Kết quả kiểm tra và giới hạn nằm trong `VERIFICATION.md`.
