"""اختبارات إدارة اتصال الأحداث."""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import realtime.routes as ws_routes
from realtime.chat_server import chat_server
from realtime.routes import events_socket


def _fake_app() -> Mock:
    """تطبيق وهمي بمصنع جلسات يعيد جلسة وهمية."""
    session = AsyncMock()

    @asynccontextmanager
    async def fake_factory():  # type: ignore[no-untyped-def]
        yield session

    app = Mock()
    app.state.session_factory = fake_factory
    return app


def test_websocket_route_registers_connection(fake_websocket, monkeypatch) -> None:
    """مسار المقبس يسجل الاتصال للمحادثة المملوكة ويحذفه عند الإغلاق."""
    user = Mock()
    user.id = uuid4()
    conversation_id = uuid4()

    async def fake_auth(websocket):  # type: ignore[no-untyped-def]
        _ = websocket
        return user

    repository = Mock()
    repository.get_owned = AsyncMock(return_value=Mock())
    monkeypatch.setattr(ws_routes, "get_current_ws_user", fake_auth)
    monkeypatch.setattr(
        ws_routes, "ConversationRepository", lambda session: repository
    )
    fake_websocket.app = _fake_app()
    asyncio.run(events_socket(fake_websocket, conversation_id))
    assert not chat_server.is_connected(str(user.id), str(conversation_id))


def test_websocket_route_rejects_unauthenticated(fake_websocket, monkeypatch) -> None:
    """مسار المقبس يغلق الاتصال برمز 4401 بلا جلسة."""

    async def fake_auth_none(websocket):  # type: ignore[no-untyped-def]
        _ = websocket
        return None

    monkeypatch.setattr(ws_routes, "get_current_ws_user", fake_auth_none)
    fake_websocket.app = _fake_app()
    asyncio.run(events_socket(fake_websocket, uuid4()))
    assert fake_websocket.closed_codes == [4401]


def test_websocket_route_rejects_untrusted_origin(
    fake_websocket, monkeypatch
) -> None:
    """مسار المقبس يغلق الاتصال برمز 4403 لمصدر غير مسموح."""
    fake_websocket.headers = {"origin": "http://evil.example"}
    fake_websocket.app = _fake_app()
    asyncio.run(events_socket(fake_websocket, uuid4()))
    assert fake_websocket.closed_codes == [4403]


def test_websocket_route_rejects_unowned_conversation(
    fake_websocket, monkeypatch
) -> None:
    """مسار المقبس يغلق الاتصال برمز 4404 لمحادثة غير مملوكة."""

    async def fake_auth(websocket):  # type: ignore[no-untyped-def]
        _ = websocket
        return Mock(id=uuid4())

    repository = Mock()
    repository.get_owned = AsyncMock(return_value=None)
    monkeypatch.setattr(ws_routes, "get_current_ws_user", fake_auth)
    monkeypatch.setattr(
        ws_routes, "ConversationRepository", lambda session: repository
    )
    fake_websocket.app = _fake_app()
    asyncio.run(events_socket(fake_websocket, uuid4()))
    assert fake_websocket.closed_codes == [4404]


def test_failed_event_has_separate_envelope(fake_websocket) -> None:
    """حدث الفشل يستخدم عقد المقبس المنفصل لا غلاف HTTP."""
    import asyncio as io

    from realtime.chat_server import chat_server, failed_event

    user_id = "user-1"
    conversation_id = "conversation-1"
    io.run(chat_server.connect(user_id, conversation_id, fake_websocket))
    try:
        io.run(
            chat_server.send_failed(
                user_id, conversation_id, "CHAT_FAILED", "تعذر إكمال المحادثة."
            )
        )
    finally:
        chat_server.disconnect(user_id, conversation_id)
    assert fake_websocket.events == [
        failed_event("CHAT_FAILED", "تعذر إكمال المحادثة.")
    ]
    assert fake_websocket.events[0]["type"] == "chat.failed"
    assert fake_websocket.events[0]["data"] is None
