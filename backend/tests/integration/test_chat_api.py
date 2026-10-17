"""اختبارات تكامل مسار المحادثة مع قناة الأحداث."""
import asyncio
from contextlib import asynccontextmanager
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

    @asynccontextmanager
    async def fake_session_factory():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[chat_routes.get_db] = fake_get_db
    app.dependency_overrides[chat_routes.get_session_factory] = (
        lambda: fake_session_factory
    )
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
        assert response.status_code == 202
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
        chat_server.disconnect(str(user.id), str(conversation_id), fake_websocket)
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


class _FailingGraph:
    """رسم يفشل أثناء البث لفحص مسار الفشل الخلفي."""

    def astream_events(self, state, config, version):  # type: ignore[no-untyped-def]
        """مولد يرمي استثناءً عند أول تكرار."""
        _ = state, config, version

        async def stream():  # type: ignore[no-untyped-def]
            raise RuntimeError("model unavailable")
            yield {}

        return stream()


def _post_chat(conversation_id):  # type: ignore[no-untyped-def]
    """إرسال رسالة قصيرة لمسار المحادثة."""
    return TestClient(app).post(
        "/api/chat",
        json={"conversation_id": str(conversation_id), "message": "مرحبًا"},
    )


def test_graph_failure_returns_202_and_emits_failed_event(fake_websocket) -> None:
    """فشل الرسم لا يغير قبول HTTP؛ يصل الفشل عبر المقبس فقط."""
    from services.chat_runs import active_chat_runs

    user = _fake_user()
    conversation_id = uuid4()
    _override_auth(user)
    app.state.graph = _FailingGraph()
    asyncio.run(chat_server.connect(str(user.id), str(conversation_id), fake_websocket))
    try:
        response = _post_chat(conversation_id)
        assert response.status_code == 202
        assert [event["type"] for event in fake_websocket.events] == [
            "chat.started",
            "chat.failed",
        ]
        assert "model unavailable" not in str(fake_websocket.events)
        # التشغيل محرر: رسالة جديدة لا تُرفض بـ CHAT_BUSY.
        assert active_chat_runs.try_begin(str(user.id), str(conversation_id))
    finally:
        chat_server.disconnect(str(user.id), str(conversation_id), fake_websocket)
        app.dependency_overrides.clear()


def test_chat_rejects_second_message_while_running(fake_websocket) -> None:
    """رسالة ثانية أثناء تشغيل نشط للمحادثة تُرفض بـ 409 CHAT_BUSY."""
    from services.chat_runs import active_chat_runs

    user = _fake_user()
    conversation_id = uuid4()
    _override_auth(user)
    asyncio.run(chat_server.connect(str(user.id), str(conversation_id), fake_websocket))
    active_chat_runs.try_begin(str(user.id), str(conversation_id))
    try:
        response = _post_chat(conversation_id)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CHAT_BUSY"
    finally:
        chat_server.disconnect(str(user.id), str(conversation_id), fake_websocket)
        app.dependency_overrides.clear()


def test_chat_rate_limit_returns_429(fake_websocket, monkeypatch) -> None:
    """تجاوز حد رسائل المستخدم يرجع 429 مع Retry-After."""
    import api.deps as deps
    from security.rate_limiter import SlidingWindowRateLimiter

    monkeypatch.setattr(deps, "chat_limiter", SlidingWindowRateLimiter(1, 60))
    user = _fake_user()
    conversation_id = uuid4()
    _override_auth(user)
    asyncio.run(chat_server.connect(str(user.id), str(conversation_id), fake_websocket))
    try:
        assert _post_chat(conversation_id).status_code == 202
        limited = _post_chat(conversation_id)
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"
        assert int(limited.headers["retry-after"]) >= 1
    finally:
        chat_server.disconnect(str(user.id), str(conversation_id), fake_websocket)
        app.dependency_overrides.clear()
