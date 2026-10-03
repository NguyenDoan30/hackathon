import json
from .base import ProviderError


class MockProvider:
    """Extractive offline provider for integration tests, not a language model."""
    name = 'mock'
    simulated = True

    def generate(self, system, prompt):
        data = json.loads(prompt)
        sources = data.get('sources', [])
        partials = data.get('partial_summaries', [])
        if not sources and not partials:
            return {'status': 'insufficient_context', 'answer': 'Không tìm thấy thông tin trong nguồn bài học.'}
        if data['task'] == 'tutor':
            return {'status': 'ok', 'answer': '[Mô phỏng — trích đoạn nguồn, không phải Gemini]\n' + '\n\n'.join(x['text'] for x in sources[:3]),
                    'citations': [x['id'] for x in sources[:3]]}
        if partials:
            return {'status': 'ok', 'summary': '[Tóm tắt mô phỏng]\n' + '\n'.join(x['summary'] for x in partials)[:1800],
                    'key_points': [p[:150] for x in partials for p in x['key_points']][:5], 'examples': [],
                    'citations': list(dict.fromkeys(c for x in partials for c in x['citations']))}
        return {'status': 'ok', 'summary': '[Tóm tắt mô phỏng — trích xuất]\n' + ' '.join(x['text'][:150] for x in sources)[:1800],
                'key_points': [x['text'][:150] for x in sources[:5]], 'examples': [],
                'citations': [x['id'] for x in sources]}
