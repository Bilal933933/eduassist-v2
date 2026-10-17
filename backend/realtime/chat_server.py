"""خادم اتصالات وأحداث المحادثة بعقد منفصل عن HTTP."""
import logging

from fastapi import WebSocket

logger = logging.getLogger("eduassist.realtime")


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
    """إدارة اتصالات الأحداث داخل الذاكرة: عدة اتصالات لكل مستخدم ومحادثة.

    الحالة محلية لعملية واحدة؛ التوسع الأفقي يتطلب ناقلًا مشتركًا (مثل Redis Pub/Sub).
    """

    def __init__(self) -> None:
        self._connections: dict[tuple[str, str], set[WebSocket]] = {}

    async def connect(
        self, user_id: str, conversation_id: str, websocket: WebSocket
    ) -> None:
        """قبول الاتصال وإضافته إلى اتصالات المحادثة (تبويبات متعددة مسموحة)."""
        await websocket.accept()
        self._connections.setdefault((user_id, conversation_id), set()).add(websocket)

    def disconnect(
        self, user_id: str, conversation_id: str, websocket: WebSocket
    ) -> None:
        """حذف هذا الاتصال فقط دون المساس باتصالات التبويبات الأخرى."""
        key = (user_id, conversation_id)
        sockets = self._connections.get(key)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            del self._connections[key]

    def is_connected(self, user_id: str, conversation_id: str) -> bool:
        """التحقق من وجود اتصال مفتوح واحد على الأقل للمحادثة."""
        return bool(self._connections.get((user_id, conversation_id)))

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
        """بث الحدث لكل اتصال حي؛ الاتصال الميت يُسقَط ولا يُفشل المعالجة."""
        sockets = list(self._connections.get((user_id, conversation_id), ()))
        for websocket in sockets:
            try:
                await websocket.send_json(event)
            except Exception:
                logger.warning(
                    "تعذر إرسال حدث %s؛ إسقاط اتصال ميت.", event.get("type")
                )
                self.disconnect(user_id, conversation_id, websocket)


chat_server = ChatServer()
