"""Gemini generateContent REST adapter. API key only in header, never logs."""
import json
import os
import re
import time
import socket
import ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .base import ProviderError
from ..schemas import Settings
from .curl_transport import request_curl
from .rate_limits import quota_error


class GeminiProvider:
    name = 'gemini'
    simulated = False

    def __init__(self, api_key=None, model=None, settings=None, transport=None):
        self._key = api_key or os.environ.get('GEMINI_API_KEY', '')
        self.model = model or os.environ.get('GEMINI_MODEL', '')
        self.settings = settings or Settings()
        self.transport = transport or os.environ.get('GEMINI_TRANSPORT', 'urllib')
        if self.transport not in ('urllib', 'curl'):
            raise ProviderError('configuration', 'GEMINI_TRANSPORT phải là urllib hoặc curl.')
        if not self._key:
            raise ProviderError('configuration', 'Thiếu GEMINI_API_KEY ở server.')
        if not re.fullmatch(r'[A-Za-z0-9._-]+', self.model):
            raise ProviderError('configuration', 'Cần GEMINI_MODEL hợp lệ được tài khoản hỗ trợ.')

    def generate(self, system, prompt):
        payload = {'systemInstruction': {'parts': [{'text': system}]},
                   'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                   'generationConfig': {'temperature': .2, 'maxOutputTokens': 4096,
                                        'responseMimeType': 'application/json'}}
        return self._generate_payload(payload)

    def _generate_payload(self, payload):
        """Shared bounded JSON transport for text and the audio adapter."""
        request = Request(f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent',
                          data=json.dumps(payload).encode(), method='POST',
                          headers={'Content-Type': 'application/json', 'x-goog-api-key': self._key})
        for attempt in range(self.settings.retries + 1):
            try:
                if self.transport == 'curl':
                    body, _ = request_curl(request.full_url, request.data, self._key, self.settings.timeout_seconds)
                else:
                    with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                        body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ProviderError('invalid_response', 'Phản hồi AI vượt giới hạn.')
                data = json.loads(body)
                candidate = (data.get('candidates') or [{}])[0]
                if candidate.get('finishReason') != 'STOP':
                    raise ProviderError('incomplete_response', 'AI bị chặn hoặc chưa trả lời đầy đủ.')
                parts = candidate.get('content', {}).get('parts', [])
                raw = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError('Expected object')
                return result
            except HTTPError as exc:
                # Hand rate limits back to the UI instead of rapidly retrying.
                if exc.code == 429:
                    raise quota_error(exc) from None
                retry = exc.code in (500, 502, 503, 504)
                if retry and attempt < self.settings.retries:
                    time.sleep(min(2 ** attempt, 4))
                    continue
                code = 'rate_limit' if exc.code == 429 else 'authentication' if exc.code in (401, 403) else 'upstream_http'
                raise ProviderError(code, f'Gemini trả lỗi HTTP {exc.code}; kiểm tra cấu hình hoặc thử lại.') from None
            except (URLError, TimeoutError, socket.timeout, ssl.SSLError) as exc:
                cause = exc.reason if isinstance(exc, URLError) else exc
                if isinstance(cause, ssl.SSLCertVerificationError):
                    raise ProviderError('tls_certificate', 'Không xác minh được chứng chỉ TLS của Google. Kiểm tra chứng chỉ và mạng trên máy; không tắt xác minh TLS.') from None
                if attempt < self.settings.retries:
                    time.sleep(min(2 ** attempt, 4))
                    continue
                if isinstance(cause, ssl.SSLError):
                    raise ProviderError('tls_connection', 'Kết nối TLS tới Google bị ngắt trước khi nhận phản hồi. Kiểm tra đường mạng hoặc chạy demo từ terminal trên máy.') from None
                if isinstance(cause, (TimeoutError, socket.timeout)):
                    raise ProviderError('timeout', 'Gemini chưa phản hồi trong thời gian cho phép. Bạn có thể thử lại.') from None
                raise ProviderError('connection', 'Không kết nối được Google Gemini. Kiểm tra kết nối mạng rồi thử lại.') from None
            except (ValueError, KeyError, TypeError, AttributeError):
                raise ProviderError('invalid_response', 'Gemini trả dữ liệu không đúng định dạng JSON.') from None
