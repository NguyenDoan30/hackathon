"""Explicit local config loading. No environment mutation, logging or execution."""
import os
from pathlib import Path
from .providers.base import ProviderError


def read_gemini_config(path=None):
    config_path = Path(path) if path is not None else Path(__file__).parent / '.env'
    values = {}
    if config_path.is_file():
        if config_path.stat().st_size > 8192:
            raise ProviderError('configuration', 'File cấu hình quá lớn.')
        try:
            contents = config_path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            raise ProviderError('configuration', 'Không đọc được file cấu hình UTF-8.') from None
        for line in contents.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                raise ProviderError('configuration', 'Mỗi dòng cấu hình phải theo dạng TEN_BIEN=gia_tri.')
            key, value = line.split('=', 1)
            key, value = key.strip(), value.strip()
            if key not in ('GEMINI_API_KEY', 'GEMINI_MODEL'):
                raise ProviderError('configuration', 'File chỉ nhận GEMINI_API_KEY và GEMINI_MODEL.')
            if key in values:
                raise ProviderError('configuration', 'Biến cấu hình bị lặp.')
            if value[:1] in ('"', "'"):
                if len(value) < 2 or value[-1] != value[0]:
                    raise ProviderError('configuration', 'Dấu nháy trong cấu hình chưa đóng.')
                value = value[1:-1]
            values[key] = value
    # Non-empty environment variables override the explicit file.
    return {key: os.environ.get(key, '').strip() or values.get(key, '')
            for key in ('GEMINI_API_KEY', 'GEMINI_MODEL')}
