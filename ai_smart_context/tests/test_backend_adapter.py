from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
import unittest
from unittest.mock import patch

from ai_smart_context import MockProvider, ProviderError
from ai_smart_context.backend_adapter import BackendAIProvider


class BackendAdapterTests(unittest.TestCase):
    def setUp(self):
        self.mock = MockProvider()
        self.adapter = BackendAIProvider(self.mock)
        self.documents = [{'id': 'doc-1', 'filename': 'SQLite.txt',
                           'content': 'SQLite giúp quản lý và truy vấn dữ liệu.'}]

    def test_exact_output_contracts_and_document_ids(self):
        result = self.adapter.chat('SQLite là gì?', self.documents, [])
        self.assertEqual(set(result), {'answer', 'sources'})
        self.assertEqual(result['sources'], ['doc-1'])
        summary = self.adapter.summarize(self.documents)
        self.assertEqual(set(summary), {'summary', 'key_points'})
        self.assertTrue(summary['summary'] and summary['key_points'])
        json.dumps([result, summary])

    def test_followup_converts_pairs_in_order(self):
        history = [{'question': 'Cơ sở dữ liệu là gì?', 'answer': 'Trả lời cũ'},
                   {'question': 'SQLite là gì?', 'answer': 'Trả lời mới'}]
        captured = []
        original = self.mock.generate
        def respond(system, prompt):
            captured.append(json.loads(prompt))
            return original(system, prompt)
        with patch.object(self.mock, 'generate', side_effect=respond):
            result = self.adapter.chat('Giải thích dễ hiểu hơn', self.documents, history)
        self.assertEqual(result['sources'], ['doc-1'])
        self.assertEqual([t['content'] for t in captured[0]['history']['recent_turns']],
                         ['Cơ sở dữ liệu là gì?', 'Trả lời cũ', 'SQLite là gì?', 'Trả lời mới'])

    def test_requests_do_not_reuse_prior_sources_or_history(self):
        self.adapter.chat('SQLite là gì?', self.documents, [])
        other = [{'id': 'doc-2', 'filename': 'Khác.txt', 'content': 'Quang hợp dùng ánh sáng.'}]
        with patch.object(self.mock, 'generate', side_effect=AssertionError('must not call')):
            self.assertEqual(self.adapter.chat('SQLite', other, [])['sources'], [])
            self.assertEqual(self.adapter.chat('Giải thích dễ hiểu hơn', other, [])['sources'], [])

    def test_concurrent_requests_keep_document_ids_separate(self):
        def call(index):
            docs = [{'id': f'doc-{index}', 'filename': 'SQLite.txt', 'content': 'SQLite truy vấn dữ liệu.'}]
            return self.adapter.chat('SQLite', docs, [])['sources']
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(call, range(10)))
        self.assertEqual(results, [[f'doc-{i}'] for i in range(10)])

    def test_no_match_does_not_call_provider(self):
        with patch.object(self.mock, 'generate', side_effect=AssertionError('must not call')):
            result = self.adapter.chat('Quang hợp dùng ánh sáng?', self.documents, [])
        self.assertEqual(result['sources'], [])
        self.assertTrue(result['answer'])

    def test_empty_or_insufficient_summary_raises_instead_of_persistable_message(self):
        with self.assertRaises(ProviderError) as error:
            self.adapter.summarize([])
        self.assertEqual(error.exception.code, 'insufficient_context')
        with patch.object(self.mock, 'generate', return_value={'status': 'insufficient_context'}):
            with self.assertRaises(ProviderError):
                self.adapter.summarize(self.documents)

    def test_duplicate_chunk_citations_map_to_one_document(self):
        docs = [{'id': 'long', 'filename': 'SQLite.txt', 'content': 'SQLite truy vấn dữ liệu. ' * 100}]
        self.assertEqual(self.adapter.chat('SQLite', docs, [])['sources'], ['long'])

    def test_malformed_documents_rejected_before_provider(self):
        for docs in (None, {}, [None], [{}], [{'id': 12, 'filename': 'x', 'content': 'SQLite'}],
                     [{'id': 'x', 'filename': 'x', 'content': ''}], self.documents * 2,
                     self.documents * 101):
            with self.subTest(type=type(docs).__name__), patch.object(self.mock, 'generate') as call:
                with self.assertRaises(ValueError):
                    self.adapter.chat('SQLite', docs, [])
                call.assert_not_called()

    def test_malformed_history_rejected_before_provider(self):
        for history in (None, {}, [None], [{}], [{'question': 'SQLite', 'answer': 12}],
                        [{'question': 'SQLite', 'answer': 'x'}] * 13):
            with self.subTest(type=type(history).__name__), patch.object(self.mock, 'generate') as call:
                with self.assertRaises(ValueError):
                    self.adapter.chat('SQLite', self.documents, history)
                call.assert_not_called()

    def test_long_backend_answer_is_bounded_without_changing_input(self):
        history = [{'question': 'SQLite là gì?', 'answer': 'x' * 100_000}]
        before = copy.deepcopy(history)
        turns = self.adapter._history(history)
        self.assertEqual(len(turns[1].content), 20_000)
        self.adapter.chat('Giải thích dễ hiểu hơn', self.documents, history)
        self.assertEqual(history, before)

    def test_inputs_not_mutated(self):
        history = [{'question': 'SQLite là gì?', 'answer': 'SQLite quản lý dữ liệu.'}]
        before = copy.deepcopy((self.documents, history))
        self.adapter.chat('SQLite', self.documents, history)
        self.adapter.summarize(self.documents)
        self.assertEqual((self.documents, history), before)

    def test_no_argument_constructor_uses_real_provider(self):
        with patch('ai_smart_context.backend_adapter.GeminiProvider', return_value=self.mock) as make:
            adapter = BackendAIProvider()
        make.assert_called_once_with(settings=None)
        self.assertEqual(adapter.chat('SQLite', self.documents, [])['sources'], ['doc-1'])

    def test_missing_key_fails_without_mock_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProviderError) as error:
                BackendAIProvider()
        self.assertEqual(error.exception.code, 'configuration')

    def test_quota_error_keeps_metadata_for_backend_caller(self):
        failure = ProviderError('rate_limit', 'Quota ngày', quota_kind='daily', retryable=False)
        with patch.object(self.mock, 'generate', side_effect=failure):
            with self.assertRaises(ProviderError) as error:
                self.adapter.chat('SQLite', self.documents, [])
        self.assertIs(error.exception, failure)
