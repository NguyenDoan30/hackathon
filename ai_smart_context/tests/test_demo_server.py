import json
import re
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from ai_smart_context.demo_server import make_server, parse_sources
from ai_smart_context import ProviderError


class DemoServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0, mock=True)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        with urlopen(cls.url) as response:
            html = response.read().decode()
        cls.token = re.search(r"const token='([^']+)'", html).group(1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def post(self, data, token=None, origin=None):
        headers = {'Content-Type': 'application/json', 'X-Demo-Token': token or self.token}
        if origin:
            headers['Origin'] = origin
        request = Request(self.url+'/api/chat', data=json.dumps(data).encode(), headers=headers)
        return urlopen(request)

    def test_reject_missing_token(self):
        with self.assertRaises(HTTPError) as error:
            self.post({}, token='wrong')
        self.assertEqual(error.exception.code, 403)

    def test_reject_other_origin(self):
        with self.assertRaises(HTTPError) as error:
            self.post({}, origin='https://example.test')
        self.assertEqual(error.exception.code, 403)

    def test_invalid_input(self):
        with self.assertRaises(HTTPError) as error:
            self.post({'sources': 'bad'})
        self.assertEqual(error.exception.code, 422)

    def test_full_http_chat(self):
        source = {'id':'local','title':'Transcript','kind':'transcript',
                  'segments':[{'text':'SQLite giúp truy vấn dữ liệu.','start_seconds':135}]}
        with self.post({'question':'SQLite truy vấn gì?','sources':[source]}) as response:
            result = json.loads(response.read())
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(result['simulated'])
        self.assertEqual(result['citations'][0]['start_seconds'], 135)

    def test_arbitrary_paths_not_served(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url+'/.env')
        self.assertEqual(error.exception.code, 404)

    def test_segments_validated(self):
        with self.assertRaises(ValueError):
            parse_sources([{'id':'x','title':'Audio','kind':'transcript','segments':[{'text':'test','start_seconds':-1}]}])

    def test_quota_metadata_reaches_ui_as_http_429(self):
        error = ProviderError('rate_limit', 'Chờ quota', retry_after_seconds=42, quota_kind='minute', retryable=True)
        with patch('ai_smart_context.demo_server.StudyAssistant.chat', side_effect=error):
            with self.assertRaises(HTTPError) as response:
                self.post({'question':'SQLite là gì?', 'sources':[{'id':'x','title':'Nguồn','text':'SQLite truy vấn dữ liệu.'}]})
            self.assertEqual(response.exception.code, 429)
            data = json.loads(response.exception.read())
            self.assertEqual(data['retry_after_seconds'], 42)
            self.assertEqual(data['quota_kind'], 'minute')
            self.assertTrue(data['retryable'])
