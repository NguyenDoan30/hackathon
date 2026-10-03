"""Gemini-backed OCR and speech-to-text adapters."""

from __future__ import annotations

import os
import re
from typing import Any

from .errors import AIProviderError, FileTooLargeError, ProcessorNotConfiguredError


# Gemini inline media requests are limited by total request size. Leave room for
# base64 encoding and the prompt, which add overhead to the original file bytes.
MAX_INLINE_MEDIA_BYTES = 14_000_000


class _GeminiProvider:
    def __init__(self, *, client: Any | None = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def _get_client(self):
        if self._client is not None:
            return self._client
        api_key = self._api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProcessorNotConfiguredError("GEMINI_API_KEY")
        try:
            from google import genai
        except ImportError as exc:
            raise ProcessorNotConfiguredError(
                "thư viện google-genai (cài file_processing/requirements.txt)"
            ) from exc
        self._client = genai.Client(api_key=api_key)
        return self._client

    @staticmethod
    def _provider_error(exc: Exception) -> AIProviderError:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc).strip()
        if not message:
            message = "No additional error details were provided."

        # Keep diagnostics useful while ensuring credentials never appear in CLI output.
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        message = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED]", message)
        message = " ".join(message.split())[:500]

        error_type = type(exc).__name__
        status = f" (HTTP {status_code})" if status_code else ""
        detail = f"Gemini {error_type}{status}: {message}"
        return AIProviderError(detail)

    @staticmethod
    def _check_size(content: bytes) -> None:
        if len(content) > MAX_INLINE_MEDIA_BYTES:
            raise FileTooLargeError(
                "Ảnh hoặc audio vượt giới hạn xử lý inline 14 MB. Hãy giảm dung lượng tệp rồi thử lại."
            )

    @staticmethod
    def _inline_part(content: bytes, mime_type: str):
        try:
            from google.genai import types
        except ImportError as exc:
            raise ProcessorNotConfiguredError(
                "thư viện google-genai (cài file_processing/requirements.txt)"
            ) from exc
        return types.Part.from_bytes(data=content, mime_type=mime_type)


class GeminiVisionOCRProvider(_GeminiProvider):
    """Read visible text from an image using Gemini multimodal input."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(client=client, api_key=api_key)
        self.model = model or os.getenv("GEMINI_VISION_MODEL", "gemini-3.8-flash")

    def extract_text(self, *, filename: str, content: bytes, mime_type: str) -> str:
        self._check_size(content)
        prompt = (
            "Đọc và chép lại toàn bộ chữ nhìn thấy trong ảnh theo thứ tự đọc tự nhiên. "
            "Giữ nguyên ngôn ngữ, dấu câu, công thức và xuống dòng khi có thể. "
            "Không tóm tắt, không giải thích, không tự bổ sung nội dung. "
            "Nếu ảnh không có chữ, trả về chuỗi rỗng. Chỉ trả về văn bản đã nhận diện."
        )
        try:
            response = self._get_client().models.generate_content(
                model=self.model,
                contents=[prompt, self._inline_part(content, mime_type)],
            )
        except (ProcessorNotConfiguredError, FileTooLargeError):
            raise
        except Exception as exc:
            raise self._provider_error(exc) from exc

        text = getattr(response, "text", "") or ""
        if not isinstance(text, str):
            raise AIProviderError("Gemini OCR trả về dữ liệu không đúng định dạng văn bản.")
        return text


class GeminiSpeechToTextProvider(_GeminiProvider):
    """Transcribe audio in its original language using Gemini audio input."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(client=client, api_key=api_key)
        self.model = model or os.getenv("GEMINI_AUDIO_MODEL", "gemini-3.8-flash")

    def transcribe(self, *, filename: str, content: bytes, mime_type: str) -> str:
        self._check_size(content)
        prompt = (
            "Hãy chép lời nói trong audio thành văn bản nguyên văn bằng đúng ngôn ngữ đang nói. "
            "Giữ tên riêng và thuật ngữ như được phát âm; không dịch, không tóm tắt, "
            "không thêm nhận xét. Chỉ trả về transcript."
        )
        try:
            response = self._get_client().models.generate_content(
                model=self.model,
                contents=[prompt, self._inline_part(content, mime_type)],
            )
        except (ProcessorNotConfiguredError, FileTooLargeError):
            raise
        except Exception as exc:
            raise self._provider_error(exc) from exc

        text = getattr(response, "text", "") or ""
        if not isinstance(text, str):
            raise AIProviderError("Gemini Speech-to-Text trả về dữ liệu không đúng định dạng văn bản.")
        return text
