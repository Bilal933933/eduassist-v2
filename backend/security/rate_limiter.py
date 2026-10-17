"""محدد معدل بنافذة منزلقة (Sliding Window) داخل الذاكرة.

الحالة محلية لعملية واحدة (Single Process): عند تشغيل أكثر من عامل (Worker)
يلزم نقل العدادات إلى مخزن مشترك مثل Redis خلف الواجهة نفسها.
"""
import math
import time
from collections import deque
from collections.abc import Callable


class SlidingWindowRateLimiter:
    """يسمح بعدد أقصى من الطلبات لكل مفتاح خلال نافذة زمنية."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        if max_requests < 1 or window_seconds <= 0:
            raise ValueError("حدود محدد المعدل يجب أن تكون موجبة.")
        self._max_requests = max_requests
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def try_acquire(self, key: str) -> int | None:
        """تسجيل طلب جديد: يعيد لا شيء عند السماح أو ثواني الانتظار عند المنع."""
        now = self._clock()
        window_start = now - self._window
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= window_start:
            hits.popleft()
        if len(hits) >= self._max_requests:
            return max(1, math.ceil(hits[0] + self._window - now))
        hits.append(now)
        if len(self._hits) > self._max_keys:
            self._evict_expired(window_start)
        return None

    def reset(self) -> None:
        """مسح كل العدادات (للاختبارات)."""
        self._hits.clear()

    def _evict_expired(self, window_start: float) -> None:
        """حذف المفاتيح التي انتهت نوافذها لمنع نمو الذاكرة بلا حد."""
        expired = [
            key
            for key, hits in self._hits.items()
            if not hits or hits[-1] <= window_start
        ]
        for key in expired:
            del self._hits[key]
