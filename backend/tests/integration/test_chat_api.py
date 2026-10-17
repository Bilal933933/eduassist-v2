"""اختبارات تكامل مسار المحادثة مع قناة الأحداث."""
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import api.routes.chat as chat_routes
from graph import build_graph
from main import app
from realtime.chat_server import chat_server


def _fake_user() -> Mock:
    """مستخدم وهمي بمعرف ثابت للاختبارات."""
    user = Mock()
    user.id = uuid4()
    user.role = "student"
    return user


def _override_auth(user: Mock | None) -> None:
    """حقن المستخدم الحالي وجلسة وهمية في اعتماديتي المسار."""
    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = message, system_prompt, temperature
        return "أهلًا بك، كيف يمكنني مساعدتك؟"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "greeting"

    app.state.graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
    )
    session = Mock()
    session.scalar = AsyncMock()
    empty_scalars = Mock()
    empty_scalars.__iter__ = Mock(return_value=iter([]))
    session.scalars = AsyncMock(return_value=empty_scalars)
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
                    "response": "أهلًا بك، كيف يمكنني مساعدتك؟",
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


def _override_auth_without_conversation(user: Mock) -> None:
    """حقن جلسة تعيد لا شيء لفحص الملكية مع مستخدم مصادق."""
    session = Mock()
    session.scalar = AsyncMock(return_value=None)

    async def fake_get_db():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[chat_routes.get_db] = fake_get_db
    app.dependency_overrides[chat_routes.get_current_user] = lambda: user


def test_missing_and_unowned_conversation_share_404() -> None:
    """الغائبة وغير المملوكة تعيدان نفس 404 بالرمز المحدد."""
    _override_auth_without_conversation(_fake_user())
    try:
        client = TestClient(app)
        for conversation_id in (uuid4(), uuid4()):
            response = client.get(f"/api/conversations/{conversation_id}/messages")
            assert response.status_code == 404
            assert response.json() == {
                "success": False,
                "error": {
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": "المحادثة غير موجودة.",
                    "details": None,
                },
            }
    finally:
        app.dependency_overrides.clear()


def test_limit_over_100_is_rejected() -> None:
    """حد أكبر من 100 مرفوض بخطأ تحقق موحد."""
    _override_auth(_fake_user())
    try:
        response = TestClient(app).get("/api/conversations", params={"limit": 101})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.clear()


def test_conversation_list_uses_paged_envelope() -> None:
    """القائمة الفارغة ترجع الغلاف {items, next_cursor}."""
    _override_auth(_fake_user())
    try:

        async def fake_empty_db():  # type: ignore[no-untyped-def]
            session = Mock()
            session.scalars = AsyncMock(
                return_value=Mock(
                    __iter__=Mock(return_value=iter([])),
                )
            )
            yield session

        app.dependency_overrides[chat_routes.get_db] = fake_empty_db
        response = TestClient(app).get("/api/conversations")
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "data": {"items": [], "next_cursor": None},
        }
    finally:
        app.dependency_overrides.clear()
