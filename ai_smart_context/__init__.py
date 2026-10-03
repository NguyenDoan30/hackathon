"""AI data contracts and providers. StudyAssistant arrives in the next commit."""
from .schemas import Source, TranscriptSegment, Turn, Settings, Chunk, Result
from .providers import Provider, ProviderError, GeminiProvider, MockProvider
from .config import read_gemini_config

__all__ = ['Source', 'TranscriptSegment', 'Turn', 'Settings', 'Chunk', 'Result',
           'Provider', 'ProviderError', 'GeminiProvider', 'MockProvider', 'read_gemini_config']
