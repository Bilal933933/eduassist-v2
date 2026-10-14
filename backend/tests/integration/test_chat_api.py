"""اختبارات تكامل مسار المحادثة مع قناة الأحداث."""
import asyncio

from fastapi.testclient import TestClient

from graph import GREETING_TEXT
from main import app
from realtime.chat_server import chat_server


def test_chat_sends_events_to_connected_frontend(fake_websocket) -> None:
    """مسار المحادثة يرسل البدء والاكتمال إلى الاتصال المسجل."""
    asyncio.run(
        chat_server.connect(
            "teacher-1",
            "conversation-1",
            fake_websocket,
        )
    )
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={
                "thread_id": "conversation-1",
                "teacher_id": "teacher-1",
                "message": "مرحبًا",
            },
        )
        assert response.status_code == 200
        assert response.json() == {
            "thread_id": "conversation-1",
            "accepted": True,
        }
        assert fake_websocket.events == [
            {"type": "started", "thread_id": "conversation-1"},
            {
                "type": "completed",
                "thread_id": "conversation-1",
                "response": GREETING_TEXT,
            },
        ]
    finally:
        chat_server.disconnect("teacher-1", "conversation-1")


def test_chat_rejects_message_without_event_connection() -> None:
    """لا تُقبل رسالة إذا لم تفتح الواجهة قناة الأحداث أولًا."""
    response = TestClient(app).post(
        "/api/chat",
        json={
            "thread_id": "conversation-without-socket",
            "teacher_id": "teacher-1",
            "message": "مرحبًا",
        },
    )
    assert response.status_code == 409
