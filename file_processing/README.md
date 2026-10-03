# File Processing

Module chuyển tài liệu đầu vào thành văn bản để Backend lưu và AI sử dụng. Module độc lập với FastAPI, database, UI, Summary và RAG.

## Phạm vi

| Đầu vào | Xử lý | Trạng thái |
| --- | --- | --- |
| PDF có lớp chữ | Trích xuất văn bản, giữ ranh giới trang | Có xử lý mặc định bằng `pypdf` |
| PDF scan/trang không có lớp chữ | Kết xuất trang thành PNG rồi OCR bằng Gemini, giữ thứ tự trang | Có fallback khi dùng `FileProcessingService.from_env()` |
| Ảnh PNG/JPG/WEBP | Nhận diện chữ OCR bằng Gemini Vision | Có sẵn qua `FileProcessingService.from_env()` |
| Audio MP3/WAV/M4A/MP4/WEBM/OGG/FLAC | Chuyển giọng nói thành transcript bằng Gemini | Có sẵn qua `FileProcessingService.from_env()` |

PDF được trích xuất lớp chữ trước. Trang không có lớp chữ sẽ được kết xuất bằng `pypdfium2` và gửi qua cùng OCR provider; metadata `pages_ocr` cho biết số trang đã gửi OCR. PDF nhiều trang có thể tạo nhiều yêu cầu Gemini.

## Cài đặt

Từ thư mục dự án:

```bash
pip install -r file_processing/requirements.txt
```

Đặt khóa API ở môi trường chạy Backend trước khi khởi động:

```text
GEMINI_API_KEY=your_gemini_api_key
```

Không ghi khóa thật vào mã nguồn hoặc GitHub. Có thể tùy chỉnh model qua `GEMINI_VISION_MODEL` và `GEMINI_AUDIO_MODEL`; mặc định cả hai dùng `gemini-3.8-flash`. Ảnh/audio dùng inline input nên giới hạn 14 MB để chừa dung lượng cho phần mã hóa request.

## Dùng với Backend

```python
from file_processing import FileProcessingService

processor = FileProcessingService.from_env()

# Trong POST /upload, Backend đọc UploadFile rồi chuyển bytes vào service.
result = processor.process(
    filename=upload.filename or "tai-lieu.pdf",
    content=await upload.read(),
    content_type=upload.content_type,
)

# Backend tự quyết định lưu Document.content vào database.
payload = result.to_dict()
```

`FileProcessingService` không mở route API, không ghi database và không gọi Summary/RAG. API key của OCR hoặc Speech-to-Text được cấu hình ở lớp adapter của nhóm, không đặt trong module này.

## Nối OCR hoặc Speech-to-Text khác (tùy chọn)

Tạo adapter đáp ứng một trong hai giao diện sau và truyền vào khi khởi tạo service:

```python
class MyOCRProvider:
    def extract_text(self, *, filename, content, mime_type) -> str:
        # Gọi SDK OCR/Vision mà nhóm thống nhất ở đây.
        ...

class MySpeechToTextProvider:
    def transcribe(self, *, filename, content, mime_type) -> str:
        # Gọi SDK Speech-to-Text mà nhóm thống nhất ở đây.
        ...

processor = FileProcessingService(
    ocr_provider=MyOCRProvider(),
    speech_to_text_provider=MySpeechToTextProvider(),
)
```

Nếu chưa đặt `GEMINI_API_KEY`, PDF vẫn dùng được; yêu cầu OCR/audio trả lỗi `processor_not_configured` để Backend chuyển thành thông báo dễ hiểu.

## Hợp đồng kết quả

```json
{
  "filename": "bai_giang.pdf",
  "file_type": "pdf",
  "status": "success",
  "text": "[Trang 1]\nNội dung đã trích xuất...",
  "mime_type": "application/pdf",
  "metadata": { "page_count": 3, "pages_with_text": 3, "pages_ocr": 0 },
  "warnings": []
}
```

Lỗi xử lý có `code`, `message` và `detail` ổn định thông qua `FileProcessingError.to_dict()`. Ví dụ: `unsupported_file_type`, `empty_file`, `file_too_large`, `invalid_file`, `no_text_found`, `processor_not_configured`.

## Ranh giới tích hợp

- Backend phụ trách `POST /upload`, đọc file, lưu dữ liệu và chuyển lỗi thành HTTP response.
- Module này chỉ kiểm tra đầu vào, nhận diện loại file và trả văn bản chuẩn hóa.
- Module AI phụ trách Summary, Smart Context/RAG và AI Tutor.
- OCR/Speech-to-Text mặc định gọi Gemini qua adapter riêng; có thể thay provider mà không đổi hợp đồng input/output của Backend.
- Nội dung ảnh/audio được gửi đến Gemini API để xử lý. Dữ liệu tệp được gửi inline và không lưu ở module này.
