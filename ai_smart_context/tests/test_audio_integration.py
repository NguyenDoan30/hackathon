import base64
import importlib.util
import json
import re
import threading
import unittest
from io import BytesIO
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ai_smart_context import GeminiProvider, ProviderError, Settings
from ai_smart_context.audio_adapter import (GeminiAudioTranscriber, TeamAudioBridge,
    audio_filename, MAX_AUDIO_BYTES)
from ai_smart_context.demo_server import make_server


class AudioProviderTests(unittest.TestCase):
    def test_multimodal_payload_and_transport(self):
        body = json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {
            'parts': [{'text': '{"transcript":"SQLite truy vấn dữ liệu."}'}]}}]}).encode()
        with patch('ai_smart_context.providers.gemini.request_curl', return_value=(body, 200)) as call:
            result = GeminiAudioTranscriber(GeminiProvider('test-key', 'test-model', transport='curl')).transcribe(
                filename='lecture.wav', content=b'RIFF-test-audio', mime_type='audio/wav')
        self.assertIn('SQLite', result)
        url, data, key, timeout = call.call_args.args
        payload = json.loads(data)
        audio = payload['contents'][0]['parts'][1]['inlineData']
        self.assertEqual(base64.b64decode(audio['data']), b'RIFF-test-audio')
        self.assertEqual(audio['mimeType'], 'audio/wav')
        self.assertNotIn('test-key', url)

    def test_oversize_and_invalid_format_do_not_call_provider(self):
        provider = Mock()
        transcriber = GeminiAudioTranscriber(provider)
        for name, data, mime in [('bad.exe', b'abc', 'audio/wav'), ('x.wav', b'', 'audio/wav'),
                                ('x.wav', b'x' * (MAX_AUDIO_BYTES + 1), 'audio/wav'),
                                ('x.wav', b'abc', 'text/html')]:
            with self.subTest(name=name, size=len(data)), self.assertRaises(ValueError):
                transcriber.transcribe(filename=name, content=data, mime_type=mime)
        provider._generate_payload.assert_not_called()

    def test_empty_malformed_or_oversize_transcript_rejected(self):
        for value in ('', None, [], 'x' * 200001):
            provider = Mock()
            provider._generate_payload.return_value = {'transcript': value}
            with self.subTest(type=type(value).__name__), self.assertRaises(ProviderError):
                GeminiAudioTranscriber(provider).transcribe(filename='x.wav', content=b'a', mime_type='audio/wav')

    def test_truncated_transcription_is_not_reported_as_success(self):
        body = b'{"candidates":[{"finishReason":"MAX_TOKENS","content":{"parts":[]}}]}'
        with patch('ai_smart_context.providers.gemini.request_curl', return_value=(body, 200)):
            with self.assertRaises(ProviderError) as error:
                GeminiAudioTranscriber(GeminiProvider('test-key', 'test-model', transport='curl')).transcribe(
                    filename='x.wav', content=b'a', mime_type='audio/wav')
        self.assertEqual(error.exception.code, 'incomplete_response')

    def test_filename_never_becomes_disk_path(self):
        self.assertEqual(audio_filename('C:\\private\\lecture.wav'), 'lecture.wav')
        self.assertEqual(audio_filename('../../lecture.mp3'), 'lecture.mp3')
        with self.assertRaises(ValueError):
            audio_filename('x\n.wav')


@unittest.skipUnless(importlib.util.find_spec('file_processing'), 'Optional teammate module not on PYTHONPATH')
class TeamAudioHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transcriber = Mock()
        cls.bridge = TeamAudioBridge(cls.transcriber)
        cls.server = make_server(0, mock=True, audio_bridge=cls.bridge)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        with urlopen(cls.url) as response:
            cls.token = re.search(r"const token='([^']+)'", response.read().decode()).group(1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.transcriber.reset_mock()
        self.transcriber.transcribe.side_effect = None
        self.transcriber.transcribe.return_value = 'SQLite  giúp quản lý và truy vấn dữ liệu.'

    def upload(self, **headers):
        fields = {'Content-Type': 'application/octet-stream', 'X-Demo-Token': self.token,
                  'X-Audio-Filename': 'bai-giang.wav', **headers}
        return urlopen(Request(self.url + '/api/transcribe', data=b'RIFF-test-audio', headers=fields), timeout=5)

    def post(self, path, data):
        with urlopen(Request(self.url + path, data=json.dumps(data).encode(), headers={
            'Content-Type': 'application/json', 'X-Demo-Token': self.token}), timeout=5) as response:
            return json.loads(response.read())

    def test_upload_team_normalization_to_chat_and_summary(self):
        with self.upload() as response:
            transcript = json.loads(response.read())
        self.assertEqual(transcript['text'], 'SQLite giúp quản lý và truy vấn dữ liệu.')
        self.assertEqual(transcript['source']['segments'], [])
        sources = [transcript['source']]
        chat = self.post('/api/chat', {'question': 'SQLite là gì?', 'sources': sources})
        summary = self.post('/api/summary', {'sources': sources})
        self.assertEqual(chat['citations'][0]['source_id'], 'transcript-user')
        self.assertIsNone(chat['citations'][0]['start_seconds'])
        self.assertTrue(summary['summary'])

    def test_token_origin_size_and_extension_guards(self):
        for headers, status in [({'X-Demo-Token': 'wrong'}, 403), ({'Origin': 'https://evil.test'}, 403),
                                ({'Content-Length': str(MAX_AUDIO_BYTES + 1)}, 413),
                                ({'X-Audio-Filename': 'x.exe'}, 422), ({'Content-Type': 'application/json'}, 415)]:
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as error:
                self.upload(**headers)
            self.assertEqual(error.exception.code, status)
            error.exception.close()
        self.transcriber.transcribe.assert_not_called()

    def test_quota_survives_teammate_error_wrapper_and_http(self):
        self.transcriber.transcribe.side_effect = ProviderError('rate_limit', 'Chờ quota',
            quota_kind='minute', retry_after_seconds=12, retryable=True)
        with self.assertRaises(HTTPError) as error:
            self.upload()
        self.assertEqual(error.exception.code, 429)
        data = json.loads(error.exception.read())
        self.assertEqual(data['retry_after_seconds'], 12)
        self.assertEqual(data['quota_kind'], 'minute')

    def test_unexpected_file_error_is_sanitized(self):
        self.transcriber.transcribe.side_effect = RuntimeError('test-secret-must-not-leak')
        with self.assertRaises(HTTPError) as error:
            self.upload()
        self.assertNotIn('test-secret', error.exception.read().decode())

    def test_missing_optional_module_keeps_mock_chat_running(self):
        server = make_server(0, mock=True)
        try:
            self.assertIsNotNone(server)
        finally:
            server.server_close()
