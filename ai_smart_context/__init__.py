"""AI data contracts, providers and stateless chat/Summary service."""
from .schemas import Source, TranscriptSegment, Turn, Settings, Chunk, Result
from .providers import Provider, ProviderError, GeminiProvider, MockProvider
from .config import read_gemini_config
from .service import StudyAssistant

__all__ = ['Source', 'TranscriptSegment', 'Turn', 'Settings', 'Chunk', 'Result',
           'Provider', 'ProviderError', 'GeminiProvider', 'MockProvider', 'read_gemini_config', 'StudyAssistant']
