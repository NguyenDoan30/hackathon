"""Per-format processors. OCR and speech recognition are injected as adapters."""

from __future__ import annotations

import io
import re
from typing import Protocol

from .errors import (
    EmptyExtractionError,
    FileTooLargeError,
    FileProcessingError,
    InvalidFileError,
    ProcessorNotConfiguredError,
)


class OCRProvider(Protocol):
    """Adapter implemented by the teammate or service providing OCR/Vision."""

    def extract_text(self, *, filename: str, content: bytes, mime_type: str) -> str:
        """Return recognized text without summarizing or answering questions."""


class SpeechToTextProvider(Protocol):
    """Adapter implemented by the teammate or service providing speech-to-text."""

    def transcribe(self, *, filename: str, content: bytes, mime_type: str) -> str:
        """Return the spoken words as a transcript."""


def _normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class PDFProcessor:
    """Extract PDF text and OCR pages that have no extractable text layer."""

    # Match the inline Gemini adapter limit while leaving room for request data.
    MAX_RENDERED_PAGE_BYTES = 14_000_000

    def __init__(self, ocr_provider: OCRProvider | None = None) -> None:
        self.ocr_provider = ocr_provider

    @staticmethod
    def _render_page_as_png(content: bytes, page_index: int) -> bytes:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise ProcessorNotConfiguredError(
                "thư viện pypdfium2 (cài file_processing/requirements.txt)"
            ) from exc

        try:
            document = pdfium.PdfDocument(content)
            try:
                page = document[page_index]
                try:
                    for scale in (2.0, 1.5, 1.0):
                        bitmap = page.render(scale=scale)
                        try:
                            buffer = io.BytesIO()
                            bitmap.to_pil().save(buffer, format="PNG", optimize=True)
                            image_bytes = buffer.getvalue()
                        finally:
                            bitmap.close()
                        if len(image_bytes) <= PDFProcessor.MAX_RENDERED_PAGE_BYTES:
                            return image_bytes
                finally:
                    page.close()
            finally:
                document.close()
        except FileProcessingError:
            raise
        except Exception as exc:
            raise InvalidFileError(
                f"Không thể kết xuất trang {page_index + 1} của PDF để OCR."
            ) from exc

        raise FileTooLargeError(
            f"Trang {page_index + 1} vẫn vượt giới hạn ảnh OCR sau khi giảm độ phân giải."
        )

    def process(self, content: bytes) -> tuple[str, dict[str, int]]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content), strict=False)
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise InvalidFileError("PDF không hợp lệ hoặc không thể đọc.") from exc

        sections: list[str] = []
        pages_with_text = 0
        pages_ocr = 0
        for page_index, extracted_text in enumerate(pages):
            text = _normalize_text(extracted_text)
            if not text and self.ocr_provider is not None:
                page_image = self._render_page_as_png(content, page_index)
                try:
                    text = self.ocr_provider.extract_text(
                        filename=f"page-{page_index + 1}.png",
                        content=page_image,
                        mime_type="image/png",
                    )
                except FileProcessingError:
                    raise
                except Exception as exc:
                    raise InvalidFileError(
                        f"Không thể nhận diện chữ trên trang {page_index + 1} của PDF."
                    ) from exc
                text = _normalize_text(text)
                pages_ocr += 1

            if text:
                pages_with_text += 1
                sections.append(f"[Trang {page_index + 1}]\n{text}")

        result = _normalize_text("\n\n".join(sections))
        if not result:
            if self.ocr_provider is None:
                raise EmptyExtractionError(
                    "PDF không có lớp văn bản. Tệp có thể là bản scan; cần OCR để đọc nội dung ảnh."
                )
            raise EmptyExtractionError("Không tìm thấy chữ trong nội dung PDF.")
        return result, {
            "page_count": len(pages),
            "pages_with_text": pages_with_text,
            "pages_ocr": pages_ocr,
        }


class ImageProcessor:
    """Extract visible text from an image through an injected OCR provider."""

    def __init__(self, provider: OCRProvider | None = None) -> None:
        self.provider = provider

    def process(self, *, filename: str, content: bytes, mime_type: str) -> str:
        if self.provider is None:
            raise ProcessorNotConfiguredError("OCR ảnh")
        try:
            text = self.provider.extract_text(
                filename=filename, content=content, mime_type=mime_type
            )
        except FileProcessingError:
            raise
        except Exception as exc:
            raise InvalidFileError("Không thể nhận diện chữ trong ảnh.") from exc
        text = _normalize_text(text)
        if not text:
            raise EmptyExtractionError("Không tìm thấy chữ trong ảnh.")
        return text


class AudioProcessor:
    """Convert an audio recording into text through an injected STT provider."""

    def __init__(self, provider: SpeechToTextProvider | None = None) -> None:
        self.provider = provider

    def process(self, *, filename: str, content: bytes, mime_type: str) -> str:
        if self.provider is None:
            raise ProcessorNotConfiguredError("Speech-to-Text")
        try:
            text = self.provider.transcribe(
                filename=filename, content=content, mime_type=mime_type
            )
        except FileProcessingError:
            raise
        except Exception as exc:
            raise InvalidFileError("Không thể chuyển nội dung ghi âm thành văn bản.") from exc
        text = _normalize_text(text)
        if not text:
            raise EmptyExtractionError("Không nghe thấy lời nói có thể chuyển thành văn bản.")
        return text
