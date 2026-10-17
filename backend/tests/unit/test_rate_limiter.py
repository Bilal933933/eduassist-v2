"""اختبارات محدد المعدل بنافذة منزلقة."""
import pytest

from security.rate_limiter import SlidingWindowRateLimiter


class _Clock:
    """ساعة يدوية لاختبار النوافذ الزمنية بلا انتظار."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_max_then_blocks_with_retry_after() -> None:
    """يسمح بالحد الأقصى ثم يمنع مع زمن انتظار موجب."""
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(3, 60, clock=clock)
    assert [limiter.try_acquire("k") for _ in range(3)] == [None, None, None]
    retry_after = limiter.try_acquire("k")
    assert retry_after == 60


def test_retry_after_shrinks_as_window_advances() -> None:
    """زمن الانتظار يتناقص مع مرور الوقت ويُسمح بعد انتهاء النافذة."""
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock=clock)
    assert limiter.try_acquire("k") is None
    clock.now += 45
    assert limiter.try_acquire("k") == 15
    clock.now += 15
    assert limiter.try_acquire("k") is None


def test_keys_are_independent() -> None:
    """استهلاك مفتاح لا يؤثر في مفتاح آخر."""
    limiter = SlidingWindowRateLimiter(1, 60, clock=_Clock())
    assert limiter.try_acquire("a") is None
    assert limiter.try_acquire("a") is not None
    assert limiter.try_acquire("b") is None


def test_blocked_attempts_do_not_extend_the_block() -> None:
    """المحاولات المحجوبة لا تُسجَّل فلا تطيل الحجب."""
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock=clock)
    limiter.try_acquire("k")
    for _ in range(5):
        clock.now += 10
        assert limiter.try_acquire("k") is not None
    clock.now += 10
    assert limiter.try_acquire("k") is None


def test_expired_keys_are_evicted_to_bound_memory() -> None:
    """المفاتيح المنتهية تُحذف عند تجاوز الحد الأقصى للمفاتيح."""
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock=clock, max_keys=3)
    for index in range(3):
        limiter.try_acquire(f"old-{index}")
    clock.now += 120
    limiter.try_acquire("new-1")
    limiter.try_acquire("new-2")
    assert set(limiter._hits) == {"new-1", "new-2"}


def test_reset_clears_state() -> None:
    """التصفير يعيد السماح فورًا."""
    limiter = SlidingWindowRateLimiter(1, 60, clock=_Clock())
    limiter.try_acquire("k")
    limiter.reset()
    assert limiter.try_acquire("k") is None


@pytest.mark.parametrize("max_requests,window", [(0, 60), (1, 0), (-1, 10)])
def test_invalid_limits_are_rejected(max_requests: int, window: float) -> None:
    """حدود غير موجبة تُرفض عند الإنشاء."""
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests, window)
