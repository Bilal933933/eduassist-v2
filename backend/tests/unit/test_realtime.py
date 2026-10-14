"""اختبارات إدارة اتصال الأحداث."""
import asyncio

from realtime.chat_server import chat_server
from realtime.routes import events_socket


def test_websocket_route_registers_connection(fake_websocket) -> None:
    """مسار المقبس يسجل الاتصال ويحذفه عند الإغلاق."""
    asyncio.run(
        events_socket(
            fake_websocket,
            "teacher-1",
            "conversation-1",
        )
    )
    assert not chat_server.is_connected("teacher-1", "conversation-1")
