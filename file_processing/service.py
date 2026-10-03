"""Small framework-independent entry point for Backend upload handlers."""

from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath

from .errors import EmptyFileError, FileTooLargeError, UnsupportedFileTypeError
from .models import FileKind, ProcessingResult, ProcessingStatus
from .processors import AudioProcessor, ImageProcessor, PDFProcessor


_EXTENSION_TYPES = {
    ".pdf": (FileKind.PDF, "application/pdf"),
    ".png": (FileKind.IMAGE, "image/png"),
    ".jpg": (FileKind.IMAGE, "image/jpeg"),
    ".jpeg": (FileKind.IMAGE, "image/jpeg"),
    ".webp": (FileKind.IMAGE, "image/webp"),
    ".mp3": (FileKind.AUDIO, "audio/mpeg"),
    ".wav": (FileKind.AUDIO, "audio/wav"),
    ".m4a": (FileKind.AUDIO, "audio/mp4"),
    ".mp4": (FileKind.AUDIO, "audio/mp4"),
    ".webm": (FileKind.AUDIO, "audio/webm"),
    ".ogg": (FileKind.AUDIO, "audio/ogg"),
    ".flac": (FileKind.AUDIO, "audio/flac"),
}


def _safe_filename(filename: str) -> str:
    # Treat both slash styles as path separators on every operating system.
    return filename.replace("\\", "/").rsplit("/", 1)[-1].strip()


class FileProcessingService:
    """Dispatch supported files and return one stable ``ProcessingResult``."""

    def __init__(
        self,
        *,
        ocr_provider=None,
        speech_to_text_provider=None,
        max_file_size_bytes: int = 20_000_000,
    ) -> None:
        if max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be greater than zero")
        self.max_file_size_bytes = max_file_size_bytes
        self.pdf_processor = PDFProcessor(ocr_provider)
        self.image_processor = ImageProcessor(ocr_provider)
        self.audio_processor = AudioProcessor(speech_to_text_provider)

    @classmethod
    def from_env(cls, *, max_file_size_bytes: int = 20_000_000) -> "FileProcessingService":
        """Create a service wired to Gemini Vision and audio transcription.

        ``GEMINI_API_KEY`` is read when a provider makes its first request. Importing
        this package does not require the Gemini SDK or an API key.
        """
        from .gemini_provider import GeminiSpeechToTextProvider, GeminiVisionOCRProvider

        return cls(
            ocr_provider=GeminiVisionOCRProvider(),
            speech_to_text_provider=GeminiSpeechToTextProvider(),
            max_file_size_bytes=max_file_size_bytes,
        )

    def process(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> ProcessingResult:
        """Process bytes from a FastAPI UploadFile or another upload handler.

        This method deliberately does not depend on FastAPI or write to a database.
        """
        safe_name = _safe_filename(filename)
        if not safe_name:
            raise UnsupportedFileTypeError("Tên tệp không hợp lệ hoặc không có phần mở rộng.")
        if not content:
            raise EmptyFileError()
        if len(content) > self.max_file_size_bytes:
            raise FileTooLargeError(
                f"Kích thước {len(content)} bytes vượt giới hạn {self.max_file_size_bytes} bytes."
            )

        extension = PurePosixPath(safe_name).suffix.lower()
        kind_and_default = _EXTENSION_TYPES.get(extension)
        if kind_and_default is None:
            guessed_type, _ = mimetypes.guess_type(safe_name)
            normalized_type = (content_type or guessed_type or "").split(";", 1)[0].lower()
            if normalized_type == "application/pdf":
                kind_and_default = (FileKind.PDF, normalized_type)
            elif normalized_type.startswith("image/"):
                kind_and_default = (FileKind.IMAGE, normalized_type)
            elif normalized_type.startswith("audio/"):
                kind_and_default = (FileKind.AUDIO, normalized_type)
            else:
                raise UnsupportedFileTypeError(f"Không hỗ trợ phần mở rộng '{extension or '(trống)'}'.")

        kind, default_mime_type = kind_and_default
        mime_type = (content_type or default_mime_type).split(";", 1)[0].strip().lower()
        warnings: list[str] = []

        if kind is FileKind.PDF:
            text, metadata = self.pdf_processor.process(content)
        elif kind is FileKind.IMAGE:
            text = self.image_processor.process(
                filename=safe_name, content=content, mime_type=mime_type
            )
            metadata = {}
        else:
            text = self.audio_processor.process(
                filename=safe_name, content=content, mime_type=mime_type
            )
            metadata = {}

        return ProcessingResult(
            filename=safe_name,
            file_type=kind,
            status=ProcessingStatus.SUCCESS,
            text=text,
            mime_type=mime_type,
            metadata=metadata,
            warnings=warnings,
        )
