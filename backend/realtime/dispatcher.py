"""موزع الأحداث (Event Dispatcher) — يرسل أحداث الرسم عبر النقل."""
from typing import AsyncIterator

from core.ports.transport import RealtimeTransport
from realtime.contracts.events import EventType, StreamEvent


class EventDispatcher:
    """يستقبل الأحداث من الرسم ويرسلها عبر النقل المختار."""

    def __init__(self, transport: RealtimeTransport) -> None:
        self.transport = transport
        self._seq = 0

    async def dispatch(
        self, event_stream: AsyncIterator[dict], thread_id: str
    ) -> None:
        """توزيع الأحداث من الرسم إلى النقل."""
        async for raw in event_stream:
            event = self._normalize(raw, thread_id)
            await self.transport.send(event)
            self._seq += 1

    def _normalize(self, raw: dict, thread_id: str) -> StreamEvent:
        """تحويل حدث لانغ غراف إلى StreamEvent."""
        # ملاحظة: هذا تنفيذ مبدئي، سيُوسَّع لاحقًا
        return StreamEvent(
            type=EventType.TRACE,
            thread_id=thread_id,
            payload=raw,
            seq=self._seq,
        )
