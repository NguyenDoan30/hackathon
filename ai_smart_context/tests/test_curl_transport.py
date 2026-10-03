import json
import ssl
import sys
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from ai_smart_context import GeminiProvider, MockProvider, ProviderError, Settings
from ai_smart_context.providers.curl_transport import request_curl, quote_config, _run_bounded, MAX_BODY


class CurlTransportTests(unittest.TestCase):
    def test_secret_in_stdin_only_and_secure_options(self):
        payload = json.dumps({'text': 'Tiếng Việt\n"quoted" \\ path'}).encode()
        with patch('ai_smart_context.providers.curl_transport.curl_executable', return_value='curl.exe'), patch('ai_smart_context.providers.curl_transport._run_bounded', return_value=(0, b'{}\n__SMART_HTTP__:200:')) as call:
            self.assertEqual(request_curl('https://generativelanguage.googleapis.com/test', payload, 'private-key'), (b'{}', 200))
            args, config, _ = call.call_args.args
            self.assertNotIn('private-key', str(args))
            self.assertIn(b'private-key', config)
            self.assertEqual(args[1], '-q')
            self.assertNotIn('--insecure', args)
            self.assertNotIn('--location', args)
            self.assertEqual(args[-2:], ['--config', '-'])
            self.assertIn(quote_config(payload.decode()).encode(), config)

    def test_config_injection_escaped(self):
        quoted = quote_config('a"\nurl = "https://evil.test/"\\')
        self.assertNotIn('\n', quoted)
        self.assertIn('\\n', quoted)
        with self.assertRaises(ProviderError):
            request_curl('https://generativelanguage.googleapis.com/test', api_key='key\r\nInjected: x')

    def test_other_destination_rejected(self):
        with self.assertRaises(ProviderError):
            request_curl('https://evil.test/')

    def test_retry_header_and_error_body_preserved_for_quota_parser(self):
        with patch('ai_smart_context.providers.curl_transport.curl_executable', return_value='curl.exe'), patch('ai_smart_context.providers.curl_transport._run_bounded', return_value=(0, b'{"error":{"details":[]}}\n__SMART_HTTP__:429:45')):
            with self.assertRaises(HTTPError) as error:
                request_curl('https://generativelanguage.googleapis.com/test')
            self.assertEqual(error.exception.headers['Retry-After'], '45')
            self.assertIn(b'"details"', error.exception.read())

    def test_exit_errors_classified_without_details(self):
        for code, expected in ((28, TimeoutError), (35, ssl.SSLError), (60, ssl.SSLCertVerificationError)):
            with self.subTest(code=code), patch('ai_smart_context.providers.curl_transport.curl_executable', return_value='curl.exe'), patch('ai_smart_context.providers.curl_transport._run_bounded', return_value=(code, b'private-key')):
                with self.assertRaises(expected) as error:
                    request_curl('https://generativelanguage.googleapis.com/test')
                self.assertNotIn('private-key', str(error.exception))

    def test_http_error_keeps_status_only(self):
        with patch('ai_smart_context.providers.curl_transport.curl_executable', return_value='curl.exe'), patch('ai_smart_context.providers.curl_transport._run_bounded', return_value=(0, b'private-key\n__SMART_HTTP__:403:')):
            with self.assertRaises(HTTPError) as error:
                request_curl('https://generativelanguage.googleapis.com/test')
            self.assertEqual(error.exception.code, 403)
            self.assertNotIn('private-key', str(error.exception))

    def test_missing_http_code_rejected(self):
        with patch('ai_smart_context.providers.curl_transport.curl_executable', return_value='curl.exe'), patch('ai_smart_context.providers.curl_transport._run_bounded', return_value=(0, b'bad')):
            with self.assertRaises(ProviderError):
                request_curl('https://generativelanguage.googleapis.com/test')

    def test_reader_stops_oversized_child(self):
        with self.assertRaises(ProviderError) as error:
            _run_bounded([sys.executable, '-c', 'import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(b"x" * 3000000)'], b'no-key', 2)
        self.assertEqual(error.exception.code, 'invalid_response')

    def test_child_small_output(self):
        code, data = _run_bounded([sys.executable, '-c', 'import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(b"{}\\n200")'], b'input', 2)
        self.assertEqual((code, data), (0, b'{}\n200'))

    def test_gemini_curl_parses_result_and_retries_503(self):
        body = json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{"status":"ok"}'}]}}]}).encode()
        with patch('ai_smart_context.providers.gemini.request_curl', side_effect=[HTTPError('https://example.test', 503, 'busy', {}, None), (body, 200)]) as call, patch('ai_smart_context.providers.gemini.time.sleep'), patch('ai_smart_context.providers.gemini.urlopen', side_effect=AssertionError('urllib must not be used')):
            result = GeminiProvider('private-key', 'test-model', Settings(retries=1), transport='curl').generate('s', 'p')
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(call.call_count, 2)

    def test_certificate_failure_does_not_retry(self):
        with patch('ai_smart_context.providers.gemini.request_curl', side_effect=ssl.SSLCertVerificationError()) as call:
            with self.assertRaises(ProviderError) as error:
                GeminiProvider('private-key', 'test-model', transport='curl').generate('s', 'p')
            self.assertEqual(error.exception.code, 'tls_certificate')
            self.assertEqual(call.call_count, 1)

    def test_invalid_transport_rejected(self):
        with self.assertRaises(ProviderError):
            GeminiProvider('private-key', 'test-model', transport='invalid')

    def test_child_timeout_terminates_process(self):
        with self.assertRaises(TimeoutError):
            _run_bounded([sys.executable, '-c', 'import time; time.sleep(30)'], b'input', 0.1)
