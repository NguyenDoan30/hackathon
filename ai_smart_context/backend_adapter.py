"""Synchronous adapter for the group's backend AIProvider v1 contract."""
from .providers import GeminiProvider, ProviderError
from .schemas import Source, Turn, require_text
from .service import StudyAssistant

# The backend supplies no lesson ID. This label is local to each call; no data
# or history is retained between calls. Ownership/filtering belong to backend.
REQUEST_LESSON = 'backend-request'


class BackendAIProvider:
    """No-argument production constructor; optional injection for offline tests."""

    def __init__(self, provider=None, settings=None):
        # Backend loads its .env into the process before constructing providers.
        # Never silently choose mock or inspect a frontend configuration file.
        self._assistant = StudyAssistant(
            provider if provider is not None else GeminiProvider(settings=settings), settings)

    @staticmethod
    def _sources(documents):
        if not isinstance(documents, list) or len(documents) > 100:
            raise ValueError('documents phải là danh sách tối đa 100 tài liệu.')
        sources = []
        for document in documents:
            if not isinstance(document, dict):
                raise ValueError('Mỗi document phải là object id/filename/content.')
            sources.append(Source(id=document.get('id'), lesson_id=REQUEST_LESSON,
                                  title=document.get('filename'), text=document.get('content')))
        return sources

    @staticmethod
    def _history(history):
        if not isinstance(history, list) or len(history) > 12:
            raise ValueError('history phải là danh sách tối đa 12 cặp question/answer.')
        turns = []
        for pair in history:
            if not isinstance(pair, dict):
                raise ValueError('Mỗi lượt history phải là object question/answer.')
            question, answer = pair.get('question'), pair.get('answer')
            require_text(question, 'history.question', 4000)
            require_text(answer, 'history.answer', 100_000)
            turns.extend((Turn('user', question, REQUEST_LESSON),
                          Turn('assistant', answer[:20_000], REQUEST_LESSON)))
        return turns

    def chat(self, question: str, documents: list[dict], history: list[dict]) -> dict:
        result = self._assistant.chat(REQUEST_LESSON, question, self._sources(documents),
                                      self._history(history))
        return {'answer': result.answer,
                'sources': list(dict.fromkeys(c['source_id'] for c in result.citations))}

    def summarize(self, documents: list[dict]) -> dict:
        result = self._assistant.summarize(REQUEST_LESSON, self._sources(documents))
        if result.status != 'ok':
            # Backend persists any returned summary. Do not save a failure
            # message as though it were a successfully generated summary.
            raise ProviderError('insufficient_context', 'Không đủ nguồn để tạo bản tóm tắt.')
        return {'summary': result.summary, 'key_points': result.key_points}
