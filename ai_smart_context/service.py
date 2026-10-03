import json
from .schemas import Result, Settings, require_text
from .retrieval import build_chunks, retrieve
from .context import history_context, is_followup, select_context, context_items
from .prompts import SYSTEM, tutor_prompt, summary_prompt
from .providers.base import ProviderError


class StudyAssistant:
    """Stateless: backend supplies only sources/history authorized for this user."""
    def __init__(self, provider, settings=None):
        self.provider = provider
        self.settings = settings or Settings()

    def ingest(self, lesson_id, sources):
        require_text(lesson_id, 'lesson_id', 200)
        return build_chunks(sources, lesson_id, self.settings)

    def _empty(self, message='Không tìm thấy đủ thông tin trong tài liệu của bài học.'):
        return Result('insufficient_context', answer=message, provider=self.provider.name,
                      simulated=self.provider.simulated)

    def _validate(self, data, allowed, summary=False):
        if not isinstance(data, dict) or data.get('status') not in ('ok', 'insufficient_context'):
            raise ProviderError('invalid_response', 'AI trả trạng thái không hợp lệ.')
        if data['status'] == 'insufficient_context':
            return self._empty()
        field = 'summary' if summary else 'answer'
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 20_000:
            raise ProviderError('invalid_response', 'Nội dung phản hồi AI không hợp lệ.')
        cited = data.get('citations')
        if not isinstance(cited, list) or not cited or len(cited) > 5000 or any(not isinstance(x, str) or x not in allowed for x in cited):
            raise ProviderError('invalid_citations', 'AI trả nguồn thiếu hoặc không thuộc context được cung cấp.')
        keys = list(dict.fromkeys(cited))
        points, examples = [], []
        if summary:
            points, examples = data.get('key_points'), data.get('examples')
            for items in (points, examples):
                if not isinstance(items, list) or len(items) > 30 or any(not isinstance(x, str) or not x.strip() or len(x) > 2000 for x in items):
                    raise ProviderError('invalid_response', 'Ý chính hoặc ví dụ không hợp lệ.')
        citations = []
        for key in keys:
            c = allowed[key]
            citations.append({'chunk_id': c.id, 'source_id': c.source_id, 'title': c.title,
                              'excerpt': c.text, 'start_seconds': c.start_seconds,
                              'end_seconds': c.end_seconds})
        return Result('ok', answer='' if summary else value, summary=value if summary else '',
                      key_points=points, examples=examples, citations=citations,
                      provider=self.provider.name, simulated=self.provider.simulated)

    def chat(self, lesson_id, question, sources, history=(), mode='standard'):
        require_text(question, 'question', 4000)
        if mode not in ('standard', 'simple', 'detailed'):
            raise ValueError('mode phải là standard, simple hoặc detailed.')
        if len(history) > 200:
            raise ValueError('Tối đa 200 lượt lịch sử mỗi yêu cầu.')
        chunks = self.ingest(lesson_id, sources)
        memory, turns = history_context(history, lesson_id, self.settings.history_chars)
        query = question
        if is_followup(question):
            # Only last USER question supplies topic; never search across other lessons.
            previous = next((t.content[:1500] for t in reversed(turns) if t.role == 'user'), '')
            if not previous:
                return self._empty('Chưa có chủ đề trước đó trong bài học để giải thích tiếp.')
            query = previous
        selected = select_context(retrieve(chunks, query, self.settings.top_k), self.settings.context_chars)
        if not selected:
            return self._empty()
        result = self._validate(self.provider.generate(SYSTEM, tutor_prompt(question, mode, context_items(selected), memory)),
                                {c.id: c for c, _ in selected})
        result.context = {'selected_chunk_ids': [c.id for c, _ in selected],
                          'context_chars': len(json.dumps(context_items(selected), ensure_ascii=False)),
                          'history_chars': len(json.dumps(memory, ensure_ascii=False)),
                          'retrieval': 'lexical_bm25', 'followup': is_followup(question)}
        return result

    def summarize(self, lesson_id, sources):
        chunks = self.ingest(lesson_id, sources)
        if not chunks:
            return self._empty('Bài học chưa có nguồn để tóm tắt.')
        batches, current = [], []
        for chunk in chunks:
            single = context_items([(chunk, 0)])
            if len(json.dumps(single, ensure_ascii=False)) > self.settings.summary_batch_chars:
                raise ValueError('Chunk vượt ngân sách summary; giảm chunk_chars.')
            tentative = context_items([(c, 0) for c in current + [chunk]])
            if len(json.dumps(tentative, ensure_ascii=False)) > self.settings.summary_batch_chars:
                batches.append(current)
                current = []
            current.append(chunk)
        if current:
            batches.append(current)
        if len(batches) > self.settings.max_summary_batches:
            raise ValueError('Tài liệu vượt ngân sách tóm tắt; chia nhỏ bài học hoặc tăng giới hạn có kiểm soát.')
        partials = []
        calls = 0
        for batch in batches:
            allowed = {c.id: c for c in batch}
            data = self.provider.generate(SYSTEM, summary_prompt(context_items([(c, 0) for c in batch])))
            calls += 1
            result = self._validate(data, allowed, summary=True)
            if result.status != 'ok':
                return result  # Never silently discard a failed part.
            partials.append({'status': 'ok', 'summary': result.summary,
                             'key_points': result.key_points, 'examples': result.examples,
                             'citations': [c['chunk_id'] for c in result.citations]})
        if len(partials) == 1:
            result.context = {'summary_batches': 1, 'provider_calls': calls, 'covered_chunks': len(chunks)}
            return result
        # Bounded reduction. Reject oversized individual outputs instead of truncating them.
        all_chunks = {c.id: c for c in chunks}
        while len(partials) > 1:
            groups, group = [], []
            for part in partials:
                if len(json.dumps(part, ensure_ascii=False)) > self.settings.summary_batch_chars // 2:
                    raise ProviderError('summary_budget', 'Bản tóm tắt trung gian quá dài; không thể tổng hợp an toàn.')
                if group and len(json.dumps(group + [part], ensure_ascii=False)) > self.settings.summary_batch_chars:
                    groups.append(group)
                    group = []
                group.append(part)
            if group:
                groups.append(group)
            if len(groups) >= len(partials):
                raise ProviderError('summary_budget', 'Không thể thu gọn các bản tóm tắt trong ngân sách.')
            reduced = []
            for group in groups:
                if len(group) == 1:
                    reduced.extend(group)
                    continue
                permitted = {cid: all_chunks[cid] for p in group for cid in p['citations']}
                result = self._validate(self.provider.generate(SYSTEM, summary_prompt([], group)), permitted, summary=True)
                calls += 1
                if result.status != 'ok':
                    return result
                reduced.append({'status': 'ok', 'summary': result.summary, 'key_points': result.key_points,
                                'examples': result.examples, 'citations': [c['chunk_id'] for c in result.citations]})
            partials = reduced
        result = self._validate(partials[0], all_chunks, summary=True)
        result.context = {'summary_batches': len(batches), 'provider_calls': calls, 'covered_chunks': len(chunks)}
        return result
