"""Run from repo root: python -m ai_smart_context.examples.backend_adapter_demo."""
import json
from ..backend_adapter import BackendAIProvider
from ..providers import MockProvider


def main():
    adapter = BackendAIProvider(provider=MockProvider())
    documents = [{'id': 'lecture-1', 'filename': 'transcript.txt',
                  'content': 'SQLite giúp quản lý và truy vấn cơ sở dữ liệu.'}]
    result = {'mode': 'Mô phỏng offline; không gọi Google, không phải Gemini thật.',
              'chat': adapter.chat('SQLite là gì?', documents, []),
              'followup': adapter.chat('Giải thích dễ hiểu hơn', documents,
                                      [{'question': 'SQLite là gì?', 'answer': 'SQLite quản lý dữ liệu.'}]),
              'summary': adapter.summarize(documents),
              'outside_context': adapter.chat('Quang hợp dùng ánh sáng?', documents, [])}
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
