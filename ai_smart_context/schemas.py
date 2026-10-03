from dataclasses import dataclass, field, asdict
from math import isfinite
from typing import Literal


def require_text(value, name, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{name}: cần chuỗi không rỗng, tối đa {limit} ký tự.')


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start_seconds: float
    end_seconds: float | None = None

    def __post_init__(self):
        require_text(self.text, 'segment.text', 200_000)
        for value in (self.start_seconds, self.end_seconds):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not isfinite(value) or value < 0):
                raise ValueError('Mốc thời gian phải là số hữu hạn không âm.')
        if self.end_seconds is not None and self.end_seconds < self.start_seconds:
            raise ValueError('end_seconds phải >= start_seconds.')


@dataclass(frozen=True)
class Source:
    id: str
    lesson_id: str
    title: str
    text: str = ''
    kind: Literal['document', 'transcript', 'note'] = 'document'
    segments: tuple[TranscriptSegment, ...] = ()

    def __post_init__(self):
        require_text(self.id, 'source.id', 200)
        require_text(self.lesson_id, 'lesson_id', 200)
        require_text(self.title, 'title', 500)
        if self.kind not in ('document', 'transcript', 'note'):
            raise ValueError('kind không hợp lệ.')
        if not isinstance(self.text, str) or len(self.text) > 1_000_000:
            raise ValueError('source.text quá dài hoặc sai kiểu.')
        if len(self.segments) > 5000 or any(not isinstance(x, TranscriptSegment) for x in self.segments):
            raise ValueError('segments không hợp lệ.')
        if self.segments and self.kind != 'transcript':
            raise ValueError('Chỉ transcript nhận segments.')
        if not self.text.strip() and not self.segments:
            raise ValueError('Nguồn phải có text hoặc segments.')
        if sum(len(x.text) for x in self.segments) > 1_000_000:
            raise ValueError('Transcript quá dài.')


@dataclass(frozen=True)
class Turn:
    role: Literal['user', 'assistant']
    content: str
    lesson_id: str

    def __post_init__(self):
        if self.role not in ('user', 'assistant'):
            raise ValueError('role phải là user hoặc assistant.')
        require_text(self.content, 'turn.content', 20_000)
        require_text(self.lesson_id, 'turn.lesson_id', 200)


@dataclass(frozen=True)
class Settings:
    chunk_chars: int = 1000
    overlap_chars: int = 120
    context_chars: int = 7000
    history_chars: int = 2200
    top_k: int = 6
    timeout_seconds: float = 30
    retries: int = 2
    summary_batch_chars: int = 9000
    max_summary_batches: int = 24

    def __post_init__(self):
        if not 200 <= self.chunk_chars <= 4000 or not 0 <= self.overlap_chars < self.chunk_chars:
            raise ValueError('Kích thước chunk/overlap không hợp lệ.')
        if not 1000 <= self.context_chars <= 30000 or not 200 <= self.history_chars <= 10000:
            raise ValueError('Ngân sách context/history không hợp lệ.')
        if not 1 <= self.top_k <= 20 or not 1 <= self.timeout_seconds <= 120 or not 0 <= self.retries <= 3:
            raise ValueError('top_k/timeout/retries không hợp lệ.')
        if not 4000 <= self.summary_batch_chars <= 30000 or not 1 <= self.max_summary_batches <= 50:
            raise ValueError('Ngân sách summary không hợp lệ.')


@dataclass(frozen=True)
class Chunk:
    id: str
    source_id: str
    lesson_id: str
    title: str
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass
class Result:
    status: str
    answer: str = ''
    summary: str = ''
    key_points: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    provider: str = ''
    simulated: bool = False

    def to_dict(self):
        return asdict(self)
