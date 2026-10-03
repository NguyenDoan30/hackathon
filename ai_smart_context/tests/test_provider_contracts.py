import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch

from ai_smart_context import GeminiProvider, MockProvider, ProviderError


class ProviderContractTests(unittest.TestCase):
    def test_missing_config_and_model_path_rejected_before_request(self):
        with patch.dict(os.environ, {}, clear=True), patch('ai_smart_context.providers.gemini.urlopen') as call:
            for key, model in (('', 'test-model'), ('test-key', ''), ('test-key', '../other')):
                with self.subTest(model=model), self.assertRaises(ProviderError) as error:
                    GeminiProvider(key, model)
                self.assertEqual(error.exception.code, 'configuration')
            call.assert_not_called()

    def test_thought_parts_are_not_joined_into_json(self):
        body = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
            {'thought': True, 'text': 'internal text'},
            {'text': '{"answer":'}, {'text': '"ok"}'}]}}]}
        with patch('ai_smart_context.providers.gemini.urlopen', return_value=BytesIO(json.dumps(body).encode())):
            result = GeminiProvider('test-key', 'test-model').generate('system', 'prompt')
        self.assertEqual(result, {'answer': 'ok'})

    def test_non_object_and_malformed_envelopes_rejected(self):
        for body in ([], {'candidates': 'invalid'}, {'candidates': [{'finishReason': 'STOP',
                'content': {'parts': [{'text': '[]'}]}}]}):
            with self.subTest(body=body), patch('ai_smart_context.providers.gemini.urlopen',
                    return_value=BytesIO(json.dumps(body).encode())):
                with self.assertRaises(ProviderError) as error:
                    GeminiProvider('test-key', 'test-model').generate('system', 'prompt')
                self.assertEqual(error.exception.code, 'invalid_response')

    def test_mock_tutor_is_explicitly_simulated_with_source_ids(self):
        provider = MockProvider()
        result = provider.generate('system', json.dumps({'task': 'tutor',
            'sources': [{'id': 'source-1', 'text': 'SQLite truy vấn dữ liệu.'}]}))
        self.assertTrue(provider.simulated)
        self.assertIn('Mô phỏng', result['answer'])
        self.assertEqual(result['citations'], ['source-1'])
        self.assertEqual(provider.generate('system', '{"task":"tutor","sources":[]}')['status'],
                         'insufficient_context')

    def test_mock_summary_merge_deduplicates_citations(self):
        partials = [{'summary': 'Nội dung', 'key_points': ['Ý chính'], 'citations': ['s1', 's1']},
                    {'summary': 'Phần sau', 'key_points': ['Ý khác'], 'citations': ['s1', 's2']}]
        result = MockProvider().generate('system', json.dumps({'task': 'summary', 'partial_summaries': partials}))
        self.assertEqual(result['citations'], ['s1', 's2'])
        self.assertEqual(result['key_points'], ['Ý chính', 'Ý khác'])
        self.assertIn('mô phỏng', result['summary'])
