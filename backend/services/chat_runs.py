"""سجل تشغيلات المحادثة النشطة: تشغيل واحد لكل مستخدم ومحادثة."""
import time
from collections.abc import Callable

# أقصى عمر لتشغيل نشط؛ بعده يُعد عالقًا ويُسمح بتشغيل جديد (حماية من تسرب العلم).
RUN_TTL_SECONDS = 300.0


class ActiveChatRuns:
    """منع تشغيلين متزامنين على نقطة التفتيش نفسها."""

    def __init__(
        self,
        ttl_seconds: float = RUN_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._started_at: dict[tuple[str, str], float] = {}

    def try_begin(self, user_id: str, conversation_id: str) -> bool:
        """حجز التشغيل: يعيد False إن كان هناك تشغيل حي للمحادثة."""
        key = (user_id, conversation_id)
        now = self._clock()
        started = self._started_at.get(key)
        if started is not None and now - started < self._ttl:
            return False
        self._started_at[key] = now
        return True

    def end(self, user_id: str, conversation_id: str) -> None:
        """تحرير الحجز (آمن عند التكرار)."""
        self._started_at.pop((user_id, conversation_id), None)

    def touch(self, user_id: str, conversation_id: str) -> None:
        """تجديد عمر التشغيل الحي؛ TTL يصبح كاشف تعليق لا سقف مدة."""
        key = (user_id, conversation_id)
        if key in self._started_at:
            self._started_at[key] = self._clock()

    def reset(self) -> None:
        """مسح كل الحجوزات (للاختبارات)."""
        self._started_at.clear()


active_chat_runs = ActiveChatRuns()
