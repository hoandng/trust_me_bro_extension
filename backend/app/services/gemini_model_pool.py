"""Process-wide cooldowns shared by request-scoped Gemini services."""
import re
import time
from datetime import datetime, timedelta
from threading import Lock
from zoneinfo import ZoneInfo

from app.core.config import settings


class GeminiQuotaExhausted(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Tất cả model Gemini đang chạm hạn mức. Vui lòng thử lại sau.")


def quota_cooldown(error) -> float:
    """Use structured quota metadata; unknown 429s receive a short cooldown."""
    details = getattr(error, 'details', None) or getattr(error, 'body', {})
    if isinstance(details, dict):
        details = details.get('error', details).get('details', [])
    if not isinstance(details, list):
        details = []
    delay = max(1, settings.gemini_quota_cooldown_seconds)
    for detail in details:
        if not isinstance(detail, dict):
            continue
        if str(detail.get('@type', '')).endswith('QuotaFailure'):
            for violation in detail.get('violations', []):
                quota_id = violation.get('quotaId', '').lower()
                if 'perday' in quota_id or 'per_day' in quota_id:
                    now = datetime.now(ZoneInfo('America/Los_Angeles'))
                    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    delay = max(delay, midnight.timestamp() - now.timestamp())
        if str(detail.get('@type', '')).endswith('RetryInfo'):
            duration = detail.get('retryDelay', '')
            if isinstance(duration, str) and re.fullmatch(r'\d+(\.\d+)?s', duration):
                delay = max(delay, float(duration[:-1]))
    response = getattr(error, 'response', None)
    if response is not None:
        retry_after = response.headers.get('Retry-After', '')
        if str(retry_after).isdigit():
            delay = max(delay, int(retry_after))
    return delay


class GeminiModelPool:
    def __init__(self):
        self._blocked_until: dict[str, float] = {}
        self._lock = Lock()

    def remaining(self, model: str) -> int:
        with self._lock:
            return max(0, int(self._blocked_until.get(model, 0) - time.monotonic() + 0.999))

    def block(self, model: str, seconds: float):
        with self._lock:
            self._blocked_until[model] = max(self._blocked_until.get(model, 0), time.monotonic() + seconds)


model_pool = GeminiModelPool()
