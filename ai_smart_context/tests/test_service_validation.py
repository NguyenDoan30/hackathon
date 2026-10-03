import json
import unittest
from unittest.mock import patch

from ai_smart_context import (StudyAssistant, Source, TranscriptSegment, Settings,
                              MockProvider, GeminiProvider, ProviderError)


class ServiceValidationTests(unittest.TestCase):
    def setUp(self):
        self.provider = MockProvider()
        self.ai = StudyAssistant(self.provider)
        self.sources = [Source('doc', 'lesson', 'SQLite', 'SQLite quản lý dữ liệu.')]

    def test_citation_deduplicated_and_metadata_from_source(self):
        source = Source('audio', 'lesson', 'Bài giảng', kind='transcript',
                        segments=(TranscriptSegment('SQLite truy vấn dữ liệu.', 135, 155),))
        def answer(system, prompt):
            cid = json.loads(prompt)['sources'][0]['id']
            return {'status': 'ok', 'answer': 'SQLite truy vấn.', 'citations': [cid, cid],
                    'start_seconds': 99999, 'source_id': 'fake'}
        with patch.object(self.provider, 'generate', side_effect=answer):
            result = self.ai.chat('lesson', 'SQLite', [source])
        self.assertEqual(len(result.citations), 1)
        self.assertEqual(result.citations[0]['source_id'], 'audio')
        self.assertEqual((result.citations[0]['start_seconds'], result.citations[0]['end_seconds']), (135, 155))

    def test_empty_foreign_or_wrong_type_citations_rejected(self):
        for citations in ([], ['fake'], [12], 'not-a-list'):
            with self.subTest(citations=citations), patch.object(self.provider, 'generate',
                    return_value={'status': 'ok', 'answer': 'SQLite', 'citations': citations}):
                with self.assertRaises(ProviderError) as error:
                    self.ai.chat('lesson', 'SQLite', self.sources)
                self.assertEqual(error.exception.code, 'invalid_citations')

    def test_invalid_summary_lists_rejected(self):
        original = self.provider.generate
        for field, value in (('key_points', None), ('key_points', [12]), ('examples', ['']),
                             ('examples', ['x' * 2001]), ('key_points', ['x'] * 31)):
            def respond(system, prompt):
                result = original(system, prompt)
                result[field] = value
                return result
            with self.subTest(field=field, value_type=type(value).__name__), patch.object(self.provider, 'generate', side_effect=respond):
                with self.assertRaises(ProviderError) as error:
                    self.ai.summarize('lesson', self.sources)
                self.assertEqual(error.exception.code, 'invalid_response')

    def test_provider_failure_propagated_without_fallback(self):
        failure = ProviderError('rate_limit', 'Quota ngày', quota_kind='daily', retryable=False)
        with patch.object(self.provider, 'generate', side_effect=failure) as call:
            with self.assertRaises(ProviderError) as error:
                self.ai.chat('lesson', 'SQLite', self.sources)
        self.assertIs(error.exception, failure)
        self.assertEqual(call.call_count, 1)

    def test_summary_second_batch_failure_does_not_report_partial_success(self):
        original = self.provider.generate
        calls = []
        def respond(system, prompt):
            calls.append(json.loads(prompt))
            if len(calls) == 2:
                return {'status': 'insufficient_context'}
            return original(system, prompt)
        sources = [Source('long', 'lesson', 'Dài', 'SQLite truy vấn dữ liệu. ' * 900)]
        with patch.object(self.provider, 'generate', side_effect=respond):
            result = self.ai.summarize('lesson', sources)
        self.assertEqual(result.status, 'insufficient_context')
        self.assertEqual(result.summary, '')
        self.assertEqual(len(calls), 2)

    def test_summary_reduction_cannot_cite_unseen_source(self):
        original = self.provider.generate
        def respond(system, prompt):
            data = json.loads(prompt)
            result = original(system, prompt)
            if data['partial_summaries']:
                result['citations'] = ['invented-source']
            return result
        with patch.object(self.provider, 'generate', side_effect=respond):
            with self.assertRaises(ProviderError) as error:
                self.ai.summarize('lesson', [Source('long', 'lesson', 'Dài', 'SQLite truy vấn. ' * 1200)])
        self.assertEqual(error.exception.code, 'invalid_citations')

    def test_summary_oversized_intermediate_not_silently_truncated(self):
        original = self.provider.generate
        def respond(system, prompt):
            result = original(system, prompt)
            result['summary'] = 'x' * 5000
            return result
        with patch.object(self.provider, 'generate', side_effect=respond):
            with self.assertRaises(ProviderError) as error:
                self.ai.summarize('lesson', [Source('long', 'lesson', 'Dài', 'SQLite truy vấn. ' * 1200)])
        self.assertEqual(error.exception.code, 'summary_budget')

    def test_summary_oversized_later_chunk_rejected_before_provider_call(self):
        ai = StudyAssistant(self.provider, Settings(chunk_chars=4000, overlap_chars=0, summary_batch_chars=4000))
        sources = [Source('small', 'lesson', 'Ngắn', 'SQLite.'),
                   Source('large', 'lesson', 'Dài', 'x' * 4000)]
        with patch.object(self.provider, 'generate', side_effect=AssertionError('budget violation reached provider')) as call:
            with self.assertRaises(ValueError):
                ai.summarize('lesson', sources)
            call.assert_not_called()

    def test_chat_summary_transcript_through_gemini_envelope(self):
        def upstream(url, body, key, timeout):
            payload = json.loads(body)
            result = MockProvider().generate(payload['systemInstruction']['parts'][0]['text'],
                payload['contents'][0]['parts'][0]['text'])
            envelope = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(result)}]}}]}
            return json.dumps(envelope).encode(), 200
        ai = StudyAssistant(GeminiProvider('test-only', 'test-model', transport='curl'))
        transcript = Source('audio', 'lesson', 'Ghi âm', kind='transcript',
                            segments=(TranscriptSegment('SQLite truy vấn dữ liệu.', 135, 155),))
        with patch('ai_smart_context.providers.gemini.request_curl', side_effect=upstream):
            self.assertTrue(ai.chat('lesson', 'SQLite', self.sources).citations)
            self.assertEqual(ai.chat('lesson', 'SQLite', [transcript]).citations[0]['start_seconds'], 135)
            self.assertTrue(ai.summarize('lesson', self.sources).key_points)
