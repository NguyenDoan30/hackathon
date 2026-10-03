"""Stable input/output models shared with the Backend and AI modules."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FileKind(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"


class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"


@dataclass(slots=True)
class ProcessingResult:
    """Normalized processor output; ``text`` is ready for a downstream AI call."""

    filename: str
    file_type: FileKind
    status: ProcessingStatus
    text: str
    mime_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation for the Backend to serialize."""
        value = asdict(self)
        value["file_type"] = self.file_type.value
        value["status"] = self.status.value
        return value
