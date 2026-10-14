"""خادم اتصالات وأحداث المحادثة."""
from fastapi import WebSocket


class ChatServer:
    """إدارة اتصال واحد داخل الذاكرة لكل مدرس ومحادثة."""

    def __init__(self) -> None:
        self._connections: dict[tuple[str, str], WebSocket] = {}

    async def connect(
        self, teacher_id: str, thread_id: str, websocket: WebSocket
    ) -> None:
        """قبول الاتصال وتسجيله."""
        await websocket.accept()
        self._connections[(teacher_id, thread_id)] = websocket

    def disconnect(self, teacher_id: str, thread_id: str) -> None:
        """حذف الاتصال إذا انتهى."""
        self._connections.pop((teacher_id, thread_id), None)

    def is_connected(self, teacher_id: str, thread_id: str) -> bool:
        """التحقق من وجود اتصال مفتوح للمحادثة."""
        return (teacher_id, thread_id) in self._connections

    async def send_started(self, teacher_id: str, thread_id: str) -> None:
        """إرسال حدث بدء معالجة الرسالة."""
        await self._send(
            teacher_id,
            thread_id,
            {"type": "started", "thread_id": thread_id},
        )

    async def send_completed(
        self, teacher_id: str, thread_id: str, response: str
    ) -> None:
        """إرسال حدث اكتمال معالجة الرسالة."""
        await self._send(
            teacher_id,
            thread_id,
            {
                "type": "completed",
                "thread_id": thread_id,
                "response": response,
            },
        )

    async def _send(
        self, teacher_id: str, thread_id: str, event: dict
    ) -> None:
        """إرسال حدث خام إلى اتصال المحادثة."""
        websocket = self._connections[(teacher_id, thread_id)]
        await websocket.send_json(event)


chat_server = ChatServer()
