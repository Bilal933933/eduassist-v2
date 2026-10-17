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
        chat_server.disconnect(user_id, conversation_id, fake_websocket)
    assert fake_websocket.events == [
        failed_event("CHAT_FAILED", "تعذر إكمال المحادثة.")
    ]
    assert fake_websocket.events[0]["type"] == "chat.failed"
    assert fake_websocket.events[0]["data"] is None


class _DeadWebSocket:
    """اتصال ميت يفشل عند أي إرسال."""

    async def accept(self) -> None:
        """محاكاة قبول الاتصال."""

    async def send_json(self, event: dict) -> None:
        """محاكاة انقطاع الاتصال أثناء الإرسال."""
        raise RuntimeError("connection closed")


def test_multiple_tabs_all_receive_events() -> None:
    """كل تبويبات المحادثة الواحدة تستقبل الحدث نفسه."""
    from tests.conftest import FakeWebSocket

    first, second = FakeWebSocket(), FakeWebSocket()

    async def scenario() -> None:
        await chat_server.connect("u-multi", "c-multi", first)
        await chat_server.connect("u-multi", "c-multi", second)
        try:
            await chat_server.send_started("u-multi", "c-multi")
        finally:
            chat_server.disconnect("u-multi", "c-multi", first)
            chat_server.disconnect("u-multi", "c-multi", second)

    asyncio.run(scenario())
    assert len(first.events) == 1
    assert first.events == second.events


def test_disconnect_removes_only_its_own_socket() -> None:
    """إغلاق تبويب لا يقطع اتصال تبويب آخر لنفس المحادثة."""
    from tests.conftest import FakeWebSocket

    first, second = FakeWebSocket(), FakeWebSocket()

    async def scenario() -> None:
        await chat_server.connect("u-own", "c-own", first)
        await chat_server.connect("u-own", "c-own", second)
        chat_server.disconnect("u-own", "c-own", first)
        assert chat_server.is_connected("u-own", "c-own")
        chat_server.disconnect("u-own", "c-own", second)
        assert not chat_server.is_connected("u-own", "c-own")

    asyncio.run(scenario())


def test_send_without_connection_does_not_raise() -> None:
    """الإرسال لمحادثة بلا اتصال يمر بصمت بدل رمي KeyError."""
    asyncio.run(chat_server.send_started("u-none", "c-none"))


def test_dead_socket_is_dropped_and_live_one_still_served() -> None:
    """الاتصال الميت يُسقَط دون منع وصول الحدث للاتصال الحي."""
    from tests.conftest import FakeWebSocket

    live = FakeWebSocket()
    dead = _DeadWebSocket()

    async def scenario() -> None:
        await chat_server.connect("u-dead", "c-dead", dead)  # type: ignore[arg-type]
        await chat_server.connect("u-dead", "c-dead", live)
        try:
            await chat_server.send_completed("u-dead", "c-dead", "رد")
            await chat_server.send_completed("u-dead", "c-dead", "رد ثانٍ")
        finally:
            chat_server.disconnect("u-dead", "c-dead", live)

    asyncio.run(scenario())
    assert [event["data"]["response"] for event in live.events] == ["رد", "رد ثانٍ"]
