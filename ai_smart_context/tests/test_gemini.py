import json
import ssl
import sys
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from ai_smart_context import GeminiProvider, MockProvider, ProviderError, Settings


class GeminiTests(unittest.TestCase):
    def make(self):
        return GeminiProvider('fake-test-key', 'test-model', Settings(retries=1))

    def response(self, result, finish='STOP'):
        raw = json.dumps({'candidates': [{'finishReason': finish, 'content': {'parts': [{'text': json.dumps(result)}]}}]}).encode()
        return BytesIO(raw)

    def test_request_contract(self):
        with patch('ai_smart_context.providers.gemini.urlopen', return_value=self.response({'status':'ok'})) as send:
            self.make().generate('system', 'prompt')
            request = send.call_args.args[0]
            self.assertNotIn('fake-test-key', request.full_url)
            self.assertEqual(request.get_header('X-goog-api-key'), 'fake-test-key')
            self.assertEqual(json.loads(request.data)['generationConfig']['responseMimeType'], 'application/json')

    def test_rate_limit_returns_without_rapid_retries(self):
        error = HTTPError('https://example.test', 429, 'rate', {}, None)
        with patch('ai_smart_context.providers.gemini.urlopen', side_effect=error) as send, patch('ai_smart_context.providers.gemini.time.sleep') as sleep:
            with self.assertRaises(ProviderError) as result:
                self.make().generate('s', 'p')
            self.assertEqual(result.exception.code, 'rate_limit')
            self.assertEqual(send.call_count, 1)
            sleep.assert_not_called()

    def test_auth_not_retried_and_no_key_in_error(self):
        with patch('ai_smart_context.providers.gemini.urlopen', side_effect=HTTPError('https://example.test',403,'fake-test-key',{},None)) as send:
            with self.assertRaises(ProviderError) as e:
                self.make().generate('s','p')
            self.assertEqual(send.call_count, 1)
            self.assertNotIn('fake-test-key', str(e.exception))

    def test_timeout_bounded(self):
        with patch('ai_smart_context.providers.gemini.urlopen', side_effect=URLError('timeout')) as send, patch('ai_smart_context.providers.gemini.time.sleep'):
            with self.assertRaises(ProviderError):
                self.make().generate('s','p')
            self.assertEqual(send.call_count, 2)

    def test_truncated_output(self):
        with patch('ai_smart_context.providers.gemini.urlopen', return_value=self.response({},'MAX_TOKENS')):
            with self.assertRaises(ProviderError):
                self.make().generate('s','p')

    def test_invalid_json(self):
        with patch('ai_smart_context.providers.gemini.urlopen', return_value=BytesIO(b'not json')):
            with self.assertRaises(ProviderError):
                self.make().generate('s','p')

    def test_tls_eof_is_not_reported_as_timeout(self):
        with patch('ai_smart_context.providers.gemini.urlopen', side_effect=URLError(ssl.SSLEOFError('test secret'))), patch('ai_smart_context.providers.gemini.time.sleep'):
            with self.assertRaises(ProviderError) as error:
                self.make().generate('s', 'p')
            self.assertEqual(error.exception.code, 'tls_connection')
            self.assertNotIn('test secret', str(error.exception))

    def test_certificate_error_not_retried(self):
        with patch('ai_smart_context.providers.gemini.urlopen', side_effect=URLError(ssl.SSLCertVerificationError('certificate'))) as call:
            with self.assertRaises(ProviderError) as error:
                self.make().generate('s', 'p')
            self.assertEqual(error.exception.code, 'tls_certificate')
            self.assertEqual(call.call_count, 1)

    def test_real_timeout_classified(self):
        with patch('ai_smart_context.providers.gemini.urlopen', side_effect=TimeoutError()), patch('ai_smart_context.providers.gemini.time.sleep'):
            with self.assertRaises(ProviderError) as error:
                self.make().generate('s', 'p')
            self.assertEqual(error.exception.code, 'timeout')
