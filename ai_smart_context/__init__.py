"""Shared AI data contracts. Provider and service arrive in subsequent commits."""
from .schemas import Source, TranscriptSegment, Turn, Settings, Chunk, Result

__all__ = ['Source', 'TranscriptSegment', 'Turn', 'Settings', 'Chunk', 'Result']
