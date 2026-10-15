"""اختبارات تكامل مسار المحادثة مع قناة الأحداث."""
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import api.routes.chat as chat_routes
from graph import GREETING_TEXT
from main import app
from realtime.chat_server import chat_server


def _fake_user() -> Mock:
    """مستخدم وهمي بمعرف ثابت للاختبارات."""
    user = Mock()
    user.id = uuid4()
    return user


def _override_auth(user: Mock | None) -> None:
    """حقن المستخدم الحالي وجلسة وهمية في اعتماديتي المسار."""
    session = Mock()
    session.scalar = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def fake_get_db():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[chat_routes.get_db] = fake_get_db
    if user is None:
        app.dependency_overrides.pop(chat_routes.get_current_user, None)
    else:
        app.dependency_overrides[chat_routes.get_current_user] = lambda: user


def test_chat_sends_events_to_connected_frontend(fake_websocket) -> None:
    """مسار المحادثة يرسل البدء والاكتمال إلى اتصال المستخدم نفسه."""
    user = _fake_user()
    conversation_id = uuid4()
    _override_auth(user)
    asyncio.run(
        chat_server.connect(
            str(user.id),
            str(conversation_id),
            fake_websocket,
        )
    )
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={
                "conversation_id": str(conversation_id),
                "message": "مرحبًا",
            },
        )
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "data": {
                "conversation_id": str(conversation_id),
                "accepted": True,
            },
        }
        assert fake_websocket.events == [
            {
                "type": "chat.started",
                "data": {"conversation_id": str(conversation_id)},
                "error": None,
            },
            {
                "type": "chat.completed",
                "data": {
                    "conversation_id": str(conversation_id),
                    "response": GREETING_TEXT,
                },
                "error": None,
            },
        ]
    finally:
        chat_server.disconnect(str(user.id), str(conversation_id))
        app.dependency_overrides.clear()


def test_chat_rejects_message_without_event_connection() -> None:
    """لا تُقبل رسالة مصادق عليها إذا لم تفتح قناة الأحداث أولًا."""
    _override_auth(_fake_user())
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={
                "conversation_id": str(uuid4()),
                "message": "مرحبًا",
            },
        )
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_chat_rejects_unauthenticated_message() -> None:
    """لا تُقبل رسالة بلا جلسة (401) حتى مع قناة مفتوحة."""
    _override_auth(None)
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={
                "conversation_id": str(uuid4()),
                "message": "مرحبًا",
            },
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
