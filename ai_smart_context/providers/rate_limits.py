"""Read only structured Google quota/retry metadata; never expose raw errors."""
import json
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .base import ProviderError


def positive_seconds(value):
    if isinstance(value, bool):
        return None
    try:
        seconds = float(value)
        return math.ceil(seconds) if math.isfinite(seconds) and 0 <= seconds <= 86400 else None
    except (ValueError, TypeError, OverflowError):
        return None


def quota_error(error):
    wait = None
    header = (error.headers or {}).get('Retry-After')
    if header:
        wait = positive_seconds(header)
        if wait is None:
            try:
                date = parsedate_to_datetime(header)
                if date.tzinfo is not None:
                    wait = positive_seconds(max(0, (date - datetime.now(timezone.utc)).total_seconds()))
            except (ValueError, TypeError, OverflowError):
                pass
    kind = 'unknown'
    try:
        raw = error.read(64001)
        data = json.loads(raw) if len(raw) <= 64000 else {}
        details = data.get('error', {}).get('details', [])
        if not isinstance(details, list):
            details = []
        for detail in details[:50]:
            if not isinstance(detail, dict):
                continue
            if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                match = re.fullmatch(r'(\d+(?:\.\d+)?)s', str(detail.get('retryDelay', '')))
                seconds = positive_seconds(match[1]) if match else None
                if seconds is not None:
                    wait = max(wait or 0, seconds)
            if detail.get('@type') == 'type.googleapis.com/google.rpc.QuotaFailure':
                violations = detail.get('violations', [])
                if not isinstance(violations, list):
                    continue
                for violation in violations[:50]:
                    if not isinstance(violation, dict):
                        continue
                    metric = str(violation.get('quotaMetric', '')) + str(violation.get('quotaId', ''))
                    metric = metric.lower()
                    if str(violation.get('quotaValue', '')) == '0':
                        kind = 'unavailable'
                    elif kind != 'unavailable' and ('perday' in metric or 'per_day' in metric):
                        kind = 'daily'
                    elif kind not in ('unavailable', 'daily') and ('perminute' in metric or 'per_minute' in metric):
                        kind = 'minute'
    except (ValueError, TypeError, AttributeError, OSError):
        pass
    if kind == 'daily':
        message = 'Google báo đã hết quota ngày của model/project. Hệ thống không tự thử lại. Kiểm tra quota và thử lại sau khi quota được đặt lại.'
    elif kind == 'unavailable':
        message = 'Google báo quota cho yêu cầu này bằng 0. Hệ thống không tự thử lại. Kiểm tra quyền sử dụng model và quota của project.'
    else:
        message = ('Gemini đang giới hạn lượt gọi hoặc token trong phút.' if kind == 'minute' else
                   'Gemini trả HTTP 429; chưa xác định được loại giới hạn từ phản hồi Google.')
        message += (f' Google yêu cầu chờ ít nhất {wait} giây.' if wait is not None else
                    ' Demo tạm chờ 60 giây; đây là thời gian dự phòng, không phải thời điểm quota chắc chắn phục hồi.')
    return ProviderError('rate_limit', message, retry_after_seconds=wait,
                         quota_kind=kind, retryable=kind not in ('daily', 'unavailable'))
