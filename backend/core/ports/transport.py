"""منفذ النقل (Transport Port) — واجهة مجردة لأي تقنية بث."""
from abc import ABC, abstractmethod

from realtime.contracts.events import StreamEvent


class RealtimeTransport(ABC):
    """
    واجهة موحدة لأي تقنية بث.

    أي تنفيذ جديد (SSE، WebSocket، NestJS) يجب أن يلتزم بهذه الواجهة.
    """

    @abstractmethod
    async def connect(self, thread_id: str, **kwargs) -> None:
        """فتح الاتصال."""
        ...

    @abstractmethod
    async def send(self, event: StreamEvent) -> None:
        """إرسال حدث واحد."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """إغلاق الاتصال."""
        ...
