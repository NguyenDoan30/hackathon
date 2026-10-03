# Demo ghi âm → transcript → AI

Chạy từ repo root khi có cả ai_smart_context và file_processing trên PYTHONPATH:

```powershell
$env:GEMINI_TRANSPORT = 'curl'
python -m ai_smart_context.demo_server --port 8054
```

Gemini đọc GEMINI_API_KEY/GEMINI_MODEL từ môi trường hoặc ai_smart_context/.env. Có thể truyền `--config PATH` để dùng file cấu hình local khác; không truyền API key trong dòng lệnh. GEMINI_AUDIO_MODEL trong môi trường có thể chọn model khác cho audio; mặc định dùng model chat. `--mock` chỉ mô phỏng chat/Summary, không giả vờ chuyển ghi âm và không gọi Gemini cho audio.

## Phần ghép

1. Người dùng chọn file và bấm **Chuyển thành văn bản**. Nút này gửi file tới server trên máy rồi tới Google Gemini; chọn file đơn thuần chỉ phát trên thiết bị.
2. Endpoint `/api/transcribe` nhận binary có token phiên, kiểm tra Host/Origin, dung lượng và phần mở rộng. File được giữ trong bộ nhớ, không ghi ra ổ đĩa.
3. TeamAudioBridge gọi FileProcessingService của người phụ trách File Processing. Code nhóm được giữ nguyên. GeminiAudioTranscriber được cắm theo SpeechToTextProvider protocol, dùng lại transport urllib/curl của module AI và bảo toàn lỗi quota qua lớp lỗi của File Processing.
4. Transcript được chuẩn hóa bởi AudioProcessor của nhóm, đưa vào vùng chỉnh sửa và tự chọn làm nguồn duy nhất. Chat/Summary sử dụng văn bản này. Đổi file xóa liên kết transcript cũ và lịch sử để tránh dùng nhầm dữ liệu.

Đã ghép với `file-processing` tại commit `114f799a282b0cba09dd6329b693bb7b1ee68893`. Nhánh AI không chứa bản sao hay sửa file của module đó. Khi ghép repo, người phụ trách tích hợp cần cung cấp module file_processing cùng phiên chạy. Nếu thiếu module, chat/Summary vẫn hoạt động và nút chuyển ghi âm không khả dụng.

## Giới hạn

- MP3/WAV/M4A/MP4/WEBM/OGG/FLAC, file không rỗng và tối đa 14.000.000 byte. Server suy MIME từ phần mở rộng, Gemini kiểm tra nội dung âm thanh. Chưa có bộ kiểm tra container chuyên sâu tại adapter.
- Theo [tài liệu Google về audio inline](https://ai.google.dev/gemini-api/docs/generate-content/audio), toàn bộ request inline phải nằm trong giới hạn 20 MB. Giới hạn file 14 MB chừa chỗ cho base64 và prompt.
- Timeout audio 90 giây mỗi lần gọi, không tự retry. Chọn 16.384 output tokens; nếu model báo MAX_TOKENS/chặn thì trả lỗi, không dùng transcript bị cắt làm thành công. Với bản ghi dài hãy chia nhỏ. Transcript tối đa 200.000 ký tự; chưa tự chia audio theo thời lượng.
- Không tạo timestamp tự động. Có thể nhập transcript kèm mốc thật qua phần nhập tay. Nội dung nhận dạng vẫn cần người dùng nghe đối chiếu, nhất là tên riêng/thuật ngữ.
- Rate-limit 429 hiển thị và khóa tạm các nút chuyển/chat/Summary; không có timer tự gửi lại. Quota ngày hoặc quota bằng 0 không tự retry.
- Server demo chỉ bind 127.0.0.1, không thay thế backend upload/auth/database của nhóm. Commit này ghép vào demo AI riêng, chưa cấu hình production backend.

## Kiểm thử

```powershell
python -m unittest discover -s ai_smart_context/tests
node ai_smart_context/verification/check_audio_ui.cjs
node ai_smart_context/verification/check_rate_limit_ui.cjs
```

123 kiểm thử Python đã đạt khi module file_processing có trên PYTHONPATH; khi thiếu module, nhóm kiểm thử phụ thuộc module này được skip rõ ràng. Kiểm thử dùng module nhóm nguyên bản, upstream speech giả để xác minh binary upload → chuẩn hóa transcript → chat/Summary, xác thực request, giới hạn, lỗi quota và dữ liệu không bị dùng nhầm. Hai kiểm thử giao diện JavaScript kiểm tra nút bận, đổi file, áp dụng nguồn và khóa quota. Chưa xác minh chất lượng nhận dạng bằng file ghi âm thật trong phiên ghép này.
