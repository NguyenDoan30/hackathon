"""Typed, user-readable errors raised by file processors."""


class FileProcessingError(Exception):
    """Base exception with a stable code suitable for an API response."""

    code = "file_processing_error"
    user_message = "Không thể xử lý tệp này. Vui lòng thử lại với tệp khác."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.user_message)
        self.detail = detail or self.user_message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.user_message, "detail": self.detail}


class UnsupportedFileTypeError(FileProcessingError):
    code = "unsupported_file_type"
    user_message = "Định dạng tệp này chưa được hỗ trợ. Hãy chọn PDF, ảnh hoặc âm thanh."


class EmptyFileError(FileProcessingError):
    code = "empty_file"
    user_message = "Tệp đang trống. Vui lòng chọn một tệp có nội dung."


class FileTooLargeError(FileProcessingError):
    code = "file_too_large"
    user_message = "Tệp vượt quá giới hạn dung lượng cho phép."


class InvalidFileError(FileProcessingError):
    code = "invalid_file"
    user_message = "Không đọc được tệp. Tệp có thể bị hỏng hoặc sai định dạng."


class EmptyExtractionError(FileProcessingError):
    code = "no_text_found"
    user_message = "Không tìm thấy văn bản có thể trích xuất trong tệp."


class ProcessorNotConfiguredError(FileProcessingError):
    code = "processor_not_configured"

    def __init__(self, processor_name: str) -> None:
        self.processor_name = processor_name
        super().__init__(f"{processor_name} chưa được kết nối với nhà cung cấp xử lý.")
        if processor_name == "GEMINI_API_KEY":
            self.user_message = "Chưa cấu hình GEMINI_API_KEY cho dịch vụ OCR và Speech-to-Text."
        elif processor_name.startswith("thư viện google-genai"):
            self.user_message = "Chưa cài thư viện Gemini cần thiết để xử lý tệp."
        elif processor_name.startswith("thư viện pypdfium2"):
            self.user_message = "Chưa cài thư viện kết xuất PDF cần thiết cho OCR."
        else:
            self.user_message = f"Chức năng {processor_name} chưa được cấu hình."


class AIProviderError(FileProcessingError):
    code = "ai_provider_error"
    user_message = "Dịch vụ AI đang gặp sự cố khi xử lý tệp. Vui lòng thử lại sau."
