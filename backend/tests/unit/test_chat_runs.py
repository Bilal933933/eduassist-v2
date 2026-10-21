"""اختبارات سجل التشغيلات النشطة."""
from services.chat_runs import ActiveChatRuns


class _Clock:
    """ساعة يدوية."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_second_begin_is_refused_until_end() -> None:
    """الحجز الثاني للمحادثة نفسها مرفوض حتى التحرير."""
    runs = ActiveChatRuns(clock=_Clock())
    assert runs.try_begin("u", "c") is True
    assert runs.try_begin("u", "c") is False
    runs.end("u", "c")
    assert runs.try_begin("u", "c") is True


def test_different_conversations_do_not_conflict() -> None:
    """المحادثات المختلفة لا تتعارض."""
    runs = ActiveChatRuns(clock=_Clock())
    assert runs.try_begin("u", "c1") is True
    assert runs.try_begin("u", "c2") is True


def test_stale_run_expires_after_ttl() -> None:
    """التشغيل العالق يُتجاوز بعد انتهاء عمره الأقصى."""
    clock = _Clock()
    runs = ActiveChatRuns(ttl_seconds=10, clock=clock)
    assert runs.try_begin("u", "c") is True
    clock.now = 11
    assert runs.try_begin("u", "c") is True


def test_touch_keeps_long_run_alive() -> None:
    """النبضة تجدد عمر التشغيل الطويل فلا يُعد عالقًا بعد TTL."""
    clock = _Clock()
    runs = ActiveChatRuns(ttl_seconds=10, clock=clock)
    assert runs.try_begin("u", "c") is True
    clock.now = 9
    runs.touch("u", "c")
    clock.now = 15
    assert runs.try_begin("u", "c") is False


def test_touch_does_not_create_a_run() -> None:
    """النبضة لا تحجز محادثة غير جارية."""
    runs = ActiveChatRuns(clock=_Clock())
    runs.touch("u", "c")
    assert runs.try_begin("u", "c") is True


def test_end_is_idempotent() -> None:
    """التحرير المتكرر آمن."""
    runs = ActiveChatRuns(clock=_Clock())
    runs.end("u", "c")
    runs.end("u", "c")
