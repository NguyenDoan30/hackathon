"""Verified HTTPS through curl. Secrets stay in stdin; output is bounded."""
import os
from pathlib import Path
import shutil
import subprocess
import threading
from urllib.error import HTTPError, URLError
import ssl
from io import BytesIO

from .base import ProviderError

MAX_BODY = 2_000_000


def curl_executable():
    # Prefer Windows' system executable, not a file in the project directory.
    if os.name == 'nt':
        candidate = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'curl.exe'
        if candidate.is_file():
            return str(candidate)
    found = shutil.which('curl')
    if not found:
        raise ProviderError('configuration', 'Không tìm thấy curl; chọn transport urllib hoặc dùng máy có curl.')
    return found


def quote_config(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t').replace('\v', '\\v') + '"'


def _run_bounded(command, config, timeout):
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, creationflags=flags)
    except OSError:
        raise ProviderError('configuration', 'Không khởi động được curl.') from None
    output = []
    failures = []

    def write_input():
        try:
            process.stdin.write(config)
            process.stdin.close()
        except (OSError, ValueError):
            pass  # Curl's exit status reports the failure; never expose input.

    def read_output():
        try:
            data = process.stdout.read(MAX_BODY + 513)
            output.append(data)
            if len(data) > MAX_BODY + 512:
                failures.append('oversize')
                process.kill()
        except (OSError, ValueError):
            failures.append('read')

    writer = threading.Thread(target=write_input, daemon=True)
    reader = threading.Thread(target=read_output, daemon=True)
    writer.start()
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
    writer.join(2)
    reader.join(2)
    if writer.is_alive() or reader.is_alive():
        raise URLError('curl pipe failure')
    process.stdin.close()
    process.stdout.close()
    if timed_out:
        raise TimeoutError()
    if 'oversize' in failures:
        raise ProviderError('invalid_response', 'Phản hồi AI vượt giới hạn.')
    if failures:
        raise URLError('curl read failure')
    return process.returncode, output[0] if output else b''


def request_curl(url, body=None, api_key=None, timeout=30):
    if not url.startswith('https://generativelanguage.googleapis.com/'):
        raise ProviderError('configuration', 'Curl chỉ kết nối HTTPS tới Google Gemini.')
    if api_key is not None and any(ord(c) < 32 or ord(c) == 127 for c in api_key):
        raise ProviderError('configuration', 'API key chứa ký tự điều khiển không hợp lệ.')
    lines = ['url = ' + quote_config(url)]
    if api_key is not None:
        lines.append('header = ' + quote_config('x-goog-api-key: ' + api_key))
    if body is not None:
        lines += ['header = "Content-Type: application/json"',
                  'data-binary = ' + quote_config(body.decode('utf-8'))]
    # -q must be first: ignore curlrc (including insecure/verbose/redirect settings).
    command = [curl_executable(), '-q', '--silent', '--proto', '=https',
               '--connect-timeout', str(min(timeout, 15)), '--max-time', str(timeout),
               '--max-filesize', str(MAX_BODY), '--write-out', '\n__SMART_HTTP__:%{http_code}:%header{retry-after}', '--config', '-']
    code, output = _run_bounded(command, ('\n'.join(lines) + '\n').encode('utf-8'), timeout)
    if code == 28:
        raise TimeoutError()
    if code in (51, 60, 77, 83, 90, 91):
        raise ssl.SSLCertVerificationError('curl certificate verification failed')
    if code == 35:
        raise ssl.SSLError('curl TLS connection failed')
    if code == 63:
        raise ProviderError('invalid_response', 'Phản hồi AI vượt giới hạn.')
    if code:
        raise URLError('curl connection failed')
    body, separator, metadata = output.rpartition(b'\n__SMART_HTTP__:')
    status, colon, retry_after = metadata.partition(b':')
    if not separator or not colon or len(retry_after) > 256 or len(status) != 3 or not status.isdigit() or not 100 <= int(status) <= 599:
        raise ProviderError('invalid_response', 'Curl không trả mã HTTP hợp lệ.')
    if len(body) > MAX_BODY:
        raise ProviderError('invalid_response', 'Phản hồi AI vượt giới hạn.')
    if not 200 <= int(status) < 300:
        headers = {'Retry-After': retry_after.decode('ascii', errors='ignore').strip()} if retry_after else {}
        raise HTTPError(url, int(status), 'Gemini HTTP error', headers, BytesIO(body))
    return body, int(status)
