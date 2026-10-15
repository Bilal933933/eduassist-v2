"""خادم اتصالات وأحداث المحادثة بعقد منفصل عن HTTP."""
from fastapi import WebSocket


def started_event(conversation_id: str) -> dict:
    """حدث بدء المعالجة: النوع والبيانات فقط."""
    return {
        "type": "chat.started",
        "data": {"conversation_id": conversation_id},
        "error": None,
    }


def completed_event(conversation_id: str, response: str) -> dict:
    """حدث اكتمال المعالجة: النوع والبيانات فقط."""
    return {
        "type": "chat.completed",
        "data": {"conversation_id": conversation_id, "response": response},
        "error": None,
    }


def failed_event(code: str, message: str) -> dict:
    """حدث الفشل: النوع والخطأ فقط."""
    return {
        "type": "chat.failed",
        "data": None,
        "error": {"code": code, "message": message},
    }


class ChatServer:
    """إدارة اتصال واحد داخل الذاكرة لكل مستخدم ومحادثة."""

    def __init__(self) -> None:
        self._connections: dict[tuple[str, str], WebSocket] = {}

    async def connect(
        self, user_id: str, conversation_id: str, websocket: WebSocket
    ) -> None:
        """قبول الاتصال وتسجيله."""
        await websocket.accept()
        self._connections[(user_id, conversation_id)] = websocket

    def disconnect(self, user_id: str, conversation_id: str) -> None:
        """حذف الاتصال إذا انتهى."""
        self._connections.pop((user_id, conversation_id), None)

    def is_connected(self, user_id: str, conversation_id: str) -> bool:
        """التحقق من وجود اتصال مفتوح للمحادثة."""
        return (user_id, conversation_id) in self._connections

    async def send_started(self, user_id: str, conversation_id: str) -> None:
        """إرسال حدث بدء معالجة الرسالة."""
        await self._send(user_id, conversation_id, started_event(conversation_id))

    async def send_completed(
        self, user_id: str, conversation_id: str, response: str
    ) -> None:
        """إرسال حدث اكتمال معالجة الرسالة."""
        await self._send(
            user_id, conversation_id, completed_event(conversation_id, response)
        )

    async def send_failed(
        self, user_id: str, conversation_id: str, code: str, message: str
    ) -> None:
        """إرسال حدث فشل معالجة الرسالة دون كشف التفاصيل."""
        await self._send(user_id, conversation_id, failed_event(code, message))

    async def _send(
        self, user_id: str, conversation_id: str, event: dict
    ) -> None:
        """إرسال حدث خام إلى اتصال المحادثة."""
        websocket = self._connections[(user_id, conversation_id)]
        await websocket.send_json(event)


chat_server = ChatServer()
