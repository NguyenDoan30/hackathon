"""Loopback-only demo server. Not the team's backend and not for deployment."""
import argparse
import json
import secrets
import threading
import os
from urllib.parse import unquote
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import StudyAssistant, Source, TranscriptSegment, Turn, GeminiProvider, MockProvider, ProviderError
from .config import read_gemini_config
from .schemas import Settings
from .audio_adapter import TeamAudioBridge, GeminiAudioTranscriber, MAX_AUDIO_BYTES, audio_filename


def parse_sources(raw):
    if not isinstance(raw, list) or len(raw) > 100:
        raise ValueError('sources phải là danh sách tối đa 100 nguồn.')
    result = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError('Nguồn dữ liệu không hợp lệ.')
        segments = item.get('segments', [])
        if not isinstance(segments, list) or len(segments) > 5000:
            raise ValueError('segments không hợp lệ.')
        parts = []
        for part in segments:
            if not isinstance(part, dict):
                raise ValueError('Segment không hợp lệ.')
            parts.append(TranscriptSegment(part.get('text'), part.get('start_seconds'), part.get('end_seconds')))
        result.append(Source(id=item.get('id'), lesson_id='lesson-1', title=item.get('title'),
                             text=item.get('text', ''), kind=item.get('kind', 'document'), segments=tuple(parts)))
    return result


def make_server(port=8051, mock=False, config_path=None, audio_bridge=None):
    token = secrets.token_urlsafe(32)
    slots = threading.BoundedSemaphore(2)
    if mock:
        ai = StudyAssistant(MockProvider())
        model = 'mock'
    else:
        cfg = read_gemini_config(config_path)
        ai = StudyAssistant(GeminiProvider(cfg['GEMINI_API_KEY'], cfg['GEMINI_MODEL']))
        model = cfg['GEMINI_MODEL']
        if audio_bridge is None:
            try:
                audio_provider = GeminiProvider(cfg['GEMINI_API_KEY'], os.environ.get('GEMINI_AUDIO_MODEL') or model,
                                                Settings(timeout_seconds=90, retries=0))
                audio_bridge = TeamAudioBridge(GeminiAudioTranscriber(audio_provider))
            except ProviderError as error:
                if error.code != 'audio_unavailable':
                    raise

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(120)

        def log_message(self, *args):
            pass  # No prompts, transcripts, credentials or request headers logged.

        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def respond(self, status, value, content_type='application/json; charset=utf-8'):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.valid_host():
                self.respond(403, {'message': 'Host không hợp lệ.'})
                return
            if self.path in ('/', '/index.html'):
                html = (Path(__file__).parent / 'demo_live.html').read_text(encoding='utf-8')
                self.respond(200, html.replace('__DEMO_TOKEN__', token).encode(), 'text/html; charset=utf-8')
            elif self.path == '/api/status':
                self.respond(200, {'provider': ai.provider.name, 'model': model, 'simulated': ai.provider.simulated,
                                  'audio_available': audio_bridge is not None, 'max_audio_bytes': MAX_AUDIO_BYTES})
            else:
                self.respond(404, {'message': 'Không tìm thấy đường dẫn.'})

        def do_POST(self):
            if not self.valid_host() or not secrets.compare_digest(self.headers.get('X-Demo-Token', ''), token):
                self.respond(403, {'message': 'Mở demo từ server trên máy để gửi yêu cầu.'})
                return
            origin = self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
                self.respond(403, {'message': 'Nguồn yêu cầu không hợp lệ.'})
                return
            if self.path == '/api/transcribe':
                self.transcribe_audio()
                return
            if self.path not in ('/api/chat', '/api/summary'):
                self.respond(404, {'message': 'Không tìm thấy đường dẫn.'})
                return
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                self.respond(415, {'message': 'Chỉ nhận JSON.'})
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 1 <= size <= 1_000_000:
                    raise ValueError('Yêu cầu quá lớn hoặc rỗng.')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Yêu cầu phải là JSON object.')
                sources = parse_sources(data.get('sources'))
                history_raw = data.get('history', [])
                if not isinstance(history_raw, list) or len(history_raw) > 50 or any(not isinstance(t, dict) for t in history_raw):
                    raise ValueError('Lịch sử không hợp lệ.')
                history = [Turn(t.get('role'), t.get('content'), 'lesson-1') for t in history_raw]
            except (ValueError, TypeError, KeyError, UnicodeError) as error:
                self.respond(422, {'code': 'input', 'message': str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else 'Dữ liệu đầu vào không hợp lệ.'})
                return
            if not slots.acquire(blocking=False):
                self.respond(429, {'code': 'busy', 'message': 'Demo đang xử lý yêu cầu khác. Vui lòng thử lại.'})
                return
            try:
                if self.path == '/api/chat':
                    result = ai.chat('lesson-1', data.get('question'), sources, history, data.get('mode', 'standard'))
                else:
                    result = ai.summarize('lesson-1', sources)
                self.respond(200, result.to_dict())
            except ValueError as error:
                self.respond(422, {'code': 'input', 'message': str(error)})
            except ProviderError as error:
                details = {'code': error.code, 'message': str(error)}
                if error.code == 'rate_limit':
                    details.update(retry_after_seconds=error.retry_after_seconds,
                                   quota_kind=error.quota_kind, retryable=error.retryable)
                self.respond(429 if error.code == 'rate_limit' else 502, details)
            except Exception:
                self.respond(500, {'code': 'internal', 'message': 'Demo gặp lỗi nội bộ; không hiển thị dữ liệu nhạy cảm.'})
            finally:
                slots.release()

        def transcribe_audio(self):
            # Raw binary upload avoids multipart/temp files and base64 browser overhead.
            self.close_connection = True
            if audio_bridge is None:
                self.respond(503, {'code': 'audio_unavailable', 'message': 'Chuyển ghi âm chưa khả dụng trên server này. Bạn vẫn có thể nhập transcript.'})
                return
            if self.headers.get('Content-Type') != 'application/octet-stream' or self.headers.get('Transfer-Encoding'):
                self.respond(415, {'code': 'input', 'message': 'Gửi bản ghi dưới dạng binary với Content-Length.'})
                return
            try:
                filename = audio_filename(unquote(self.headers.get('X-Audio-Filename', ''), errors='strict'))
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_AUDIO_BYTES:
                    self.respond(413, {'code': 'audio_size', 'message': 'Chọn bản ghi không rỗng, tối đa 14 MB.'})
                    return
            except (ValueError, UnicodeError):
                self.respond(422, {'code': 'input', 'message': 'Tên hoặc kích thước bản ghi không hợp lệ.'})
                return
            if not slots.acquire(blocking=False):
                self.respond(429, {'code': 'busy', 'message': 'Demo đang bận. Hãy thử lại sau.'})
                return
            try:
                body = self.rfile.read(size)
                if len(body) != size:
                    raise ValueError('Bản ghi chưa tải lên đầy đủ.')
                result = audio_bridge.process(filename, body)
                self.respond(200, result)
            except ValueError:
                self.respond(422, {'code': 'input', 'message': 'Không đọc được bản ghi. Chọn lại file âm thanh hợp lệ.'})
            except ProviderError as error:
                details = {'code': error.code, 'message': str(error)}
                if error.code == 'rate_limit':
                    details.update(retry_after_seconds=error.retry_after_seconds, quota_kind=error.quota_kind,
                                   retryable=error.retryable)
                self.respond(429 if error.code == 'rate_limit' else 502, details)
            except Exception:
                self.respond(500, {'code': 'audio_processing', 'message': 'Không chuyển được bản ghi. Bạn có thể thử lại hoặc nhập transcript.'})
            finally:
                slots.release()

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8051)
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--config', help='Explicit server-side Gemini config file path; never a key value.')
    args = parser.parse_args()
    server = make_server(args.port, args.mock, args.config)
    print(f'AI demo: http://127.0.0.1:{server.server_port} (loopback only)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
