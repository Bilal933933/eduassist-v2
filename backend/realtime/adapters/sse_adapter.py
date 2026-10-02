"""محول SSE (SSE Adapter) — تنفيذ النقل عبر أحداث مرسلة من الخادم."""
import asyncio
import json
from typing import AsyncIterator

from core.ports.transport import RealtimeTransport
from core.events import EventType, StreamEvent


class SSEAdapter(RealtimeTransport):
    """تنفيذ النقل عبر SSE."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self.thread_id: str = ""

    async def connect(self, thread_id: str, **kwargs) -> None:
        self.thread_id = thread_id

    async def send(self, event: StreamEvent) -> None:
        await self._queue.put(event)

    async def close(self) -> None:
        await self._queue.put(None)

    async def stream(self) -> AsyncIterator[str]:
        """توليد نص SSE جاهز للإرسال."""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield self._format_sse(event)
            if event.type in (EventType.DONE, EventType.ERROR):
                break

    @staticmethod
    def _format_sse(event: StreamEvent) -> str:
        """تنسيق الحدث كـ SSE."""
        data = json.dumps(event.payload, ensure_ascii=False)
        return f"event: {event.type.value}\ndata: {data}\n\n"
