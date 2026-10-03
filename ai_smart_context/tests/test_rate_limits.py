import json
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
from ai_smart_context import GeminiProvider, ProviderError, Settings
from ai_smart_context.providers.rate_limits import quota_error


def response(details=(), headers=None, raw=None):
    body = raw if raw is not None else json.dumps({'error': {'message': 'private-key', 'details': list(details)}}).encode()
    return HTTPError('https://example.test', 429, 'private-key', headers or {}, BytesIO(body))


def violation(quota_id, value='10'):
    return {'@type': 'type.googleapis.com/google.rpc.QuotaFailure',
            'violations': [{'quotaId': quota_id, 'quotaValue': value}]}


class RateLimitTests(unittest.TestCase):
    def test_retry_info_and_header_use_longest_delay(self):
        error = quota_error(response([{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '8.2s'}, violation('GenerateRequestsPerMinutePerProject')], {'Retry-After': '12'}))
        self.assertEqual(error.retry_after_seconds, 12)
        self.assertEqual(error.quota_kind, 'minute')
        self.assertTrue(error.retryable)
        self.assertNotIn('private-key', str(error))

    def test_daily_quota_is_not_retryable(self):
        error = quota_error(response([violation('GenerateRequestsPerDayPerProject')]))
        self.assertEqual(error.quota_kind, 'daily')
        self.assertFalse(error.retryable)

    def test_zero_quota_is_not_retryable(self):
        error = quota_error(response([violation('GenerateRequestsPerMinute', '0'), violation('GenerateRequestsPerDay')]))
        self.assertEqual(error.quota_kind, 'unavailable')
        self.assertFalse(error.retryable)

    def test_unknown_limit_does_not_claim_daily_or_exact_reset(self):
        error = quota_error(response(raw=b'not JSON private-key'))
        self.assertEqual(error.quota_kind, 'unknown')
        self.assertIsNone(error.retry_after_seconds)
        self.assertIn('dự phòng', str(error))
        self.assertNotIn('private-key', str(error))

    def test_invalid_delay_is_ignored(self):
        error = quota_error(response([{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '-10s'}], {'Retry-After': 'NaN'}))
        self.assertIsNone(error.retry_after_seconds)

    def test_malformed_metadata_safe(self):
        for raw in (b'[]', b'{"error":[]}', b'{"error":{"details":[null,{"violations":"bad","@type":"type.googleapis.com/google.rpc.QuotaFailure"}]}}'):
            with self.subTest(raw=raw):
                self.assertEqual(quota_error(response(raw=raw)).quota_kind, 'unknown')

    def test_curl_429_does_not_retry(self):
        with patch('ai_smart_context.providers.gemini.request_curl', side_effect=response([violation('GenerateRequestsPerDay')])), patch('ai_smart_context.providers.gemini.time.sleep') as sleep:
            with self.assertRaises(ProviderError) as error:
                GeminiProvider('private-key', 'test-model', Settings(retries=2), transport='curl').generate('s', 'p')
            self.assertEqual(error.exception.quota_kind, 'daily')
            sleep.assert_not_called()
