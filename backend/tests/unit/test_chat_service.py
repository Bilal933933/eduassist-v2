"""اختبارات قبول المحادثة وتشغيلها الخلفي بعزل القاعدة والرسم."""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

import services.chat_service as chat_service
from realtime.chat_server import chat_server
from services.chat_runs import active_chat_runs
from services.chat_service import AcceptedChat, accept_chat, run_chat
from services.errors import (
    ChatBusyError,
    ConversationNotFoundError,
    EventConnectionRequiredError,
)
from tests.conftest import FakeWebSocket


class _FakeGraph:
    """رسم وهمي يبث ردًا أو يفشل."""

    def __init__(self, response: str | None = None, error: Exception | None = None):
        self._response = response
        self._error = error

    def astream_events(self, state, config, version):  # type: ignore[no-untyped-def]
        """مولد أحداث على نمط LangGraph."""
        _ = state, config, version

        async def stream():  # type: ignore[no-untyped-def]
            if self._error is not None:
                raise self._error
            if self._response is not None:
                yield {
                    "event": "on_chain_end",
                    "data": {"output": {"response": self._response}},
                }

        return stream()


class _Env:
    """بيئة اختبار: مستودعات وهمية ومصنع جلسات."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, conversation: object | None):
        self.session = Mock()
        self.session.commit = AsyncMock()
        self.conversation = conversation
        self.messages = Mock()
        self.messages.list_recent = AsyncMock(return_value=[])
        self.messages.add = AsyncMock()
        conversations = Mock()
        conversations.get_owned = AsyncMock(return_value=conversation)
        monkeypatch.setattr(chat_service, "MessageRepository", lambda s: self.messages)
        monkeypatch.setattr(chat_service, "ConversationRepository", lambda s: conversations)

        @asynccontextmanager
        async def factory():  # type: ignore[no-untyped-def]
            yield self.session

        self.factory = factory


def _accepted(user_id=None, conversation_id=None) -> AcceptedChat:  # type: ignore[no-untyped-def]
    """رسالة مقبولة جاهزة للتشغيل."""
    return AcceptedChat(
        user_id=user_id or uuid4(),
        conversation_id=conversation_id or uuid4(),
        message="مرحبًا",
        user_role="student",
        context={"history": []},
    )


def test_accept_requires_event_connection(monkeypatch) -> None:
    """بلا اتصال أحداث يُرفض القبول قبل لمس القاعدة."""
    env = _Env(monkeypatch, conversation=Mock())
    with pytest.raises(EventConnectionRequiredError):
        asyncio.run(accept_chat(env.session, uuid4(), uuid4(), "مرحبًا"))
    env.messages.add.assert_not_awaited()


def test_accept_rejects_unowned_conversation(monkeypatch) -> None:
    """المحادثة غير المملوكة تُرفض ولا تحجز تشغيلًا."""
    env = _Env(monkeypatch, conversation=None)
    user_id, conversation_id = uuid4(), uuid4()
    socket = FakeWebSocket()

    async def scenario() -> None:
        await chat_server.connect(str(user_id), str(conversation_id), socket)
        try:
            with pytest.raises(ConversationNotFoundError):
                await accept_chat(env.session, user_id, conversation_id, "مرحبًا")
        finally:
            chat_server.disconnect(str(user_id), str(conversation_id), socket)

    asyncio.run(scenario())
    assert active_chat_runs.try_begin(str(user_id), str(conversation_id))


def test_accept_saves_message_and_blocks_concurrent_run(monkeypatch) -> None:
    """القبول يحفظ الرسالة ويحجز التشغيل فتُرفض الرسالة المتزامنة."""
    env = _Env(monkeypatch, conversation=Mock())
    user_id, conversation_id = uuid4(), uuid4()
    socket = FakeWebSocket()

    async def scenario() -> AcceptedChat:
        await chat_server.connect(str(user_id), str(conversation_id), socket)
        try:
            accepted = await accept_chat(env.session, user_id, conversation_id, "سؤال")
            with pytest.raises(ChatBusyError):
                await accept_chat(env.session, user_id, conversation_id, "سؤال ثانٍ")
            return accepted
        finally:
            chat_server.disconnect(str(user_id), str(conversation_id), socket)

    accepted = asyncio.run(scenario())
    assert accepted.message == "سؤال"
    env.messages.add.assert_awaited_once_with(conversation_id, user_id, "user", "سؤال")
    env.session.commit.assert_awaited_once()


def test_accept_failure_releases_the_run(monkeypatch) -> None:
    """فشل الحفظ أثناء القبول لا يترك المحادثة محجوزة."""
    env = _Env(monkeypatch, conversation=Mock())
    env.messages.add = AsyncMock(side_effect=RuntimeError("db down"))
    user_id, conversation_id = uuid4(), uuid4()
    socket = FakeWebSocket()

    async def scenario() -> None:
        await chat_server.connect(str(user_id), str(conversation_id), socket)
        try:
            with pytest.raises(RuntimeError):
                await accept_chat(env.session, user_id, conversation_id, "سؤال")
        finally:
            chat_server.disconnect(str(user_id), str(conversation_id), socket)

    asyncio.run(scenario())
    assert active_chat_runs.try_begin(str(user_id), str(conversation_id))


def _run(monkeypatch, graph, socket, conversation=None):  # type: ignore[no-untyped-def]
    """تشغيل run_chat مع اتصال مفتوح وإرجاع الرسالة المقبولة والبيئة."""
    env = _Env(monkeypatch, conversation=conversation or Mock())
    accepted = _accepted()
    owner, conv = str(accepted.user_id), str(accepted.conversation_id)
    active_chat_runs.try_begin(owner, conv)

    async def scenario() -> None:
        await chat_server.connect(owner, conv, socket)
        try:
            await run_chat(graph, env.factory, accepted)
        finally:
            chat_server.disconnect(owner, conv, socket)

    asyncio.run(scenario())
    return accepted, env


def test_run_chat_success_saves_reply_and_emits_events(monkeypatch) -> None:
    """النجاح يحفظ رد المساعد بجلسة مستقلة ويبث البدء والاكتمال ويحرر التشغيل."""
    socket = FakeWebSocket()
    accepted, env = _run(monkeypatch, _FakeGraph(response="أهلًا"), socket)
    assert [e["type"] for e in socket.events] == ["chat.started", "chat.completed"]
    assert socket.events[1]["data"]["response"] == "أهلًا"
    env.messages.add.assert_awaited_once_with(
        accepted.conversation_id, accepted.user_id, "assistant", "أهلًا"
    )
    env.session.commit.assert_awaited_once()
    assert active_chat_runs.try_begin(str(accepted.user_id), str(accepted.conversation_id))


def test_run_chat_graph_error_emits_failed_without_raising(monkeypatch) -> None:
    """فشل الرسم يبث chat.failed دون تسريب السبب ولا يرمي ويحرر التشغيل."""
    socket = FakeWebSocket()
    accepted, env = _run(monkeypatch, _FakeGraph(error=RuntimeError("secret")), socket)
    assert [e["type"] for e in socket.events] == ["chat.started", "chat.failed"]
    assert "secret" not in str(socket.events)
    env.messages.add.assert_not_awaited()
    assert active_chat_runs.try_begin(str(accepted.user_id), str(accepted.conversation_id))


def test_run_chat_without_response_emits_failed(monkeypatch) -> None:
    """رسم ينتهي بلا رد يُعد فشلًا ولا يحفظ رسالة فارغة."""
    socket = FakeWebSocket()
    _, env = _run(monkeypatch, _FakeGraph(response=None), socket)
    assert socket.events[-1]["type"] == "chat.failed"
    env.messages.add.assert_not_awaited()


def test_run_chat_with_empty_response_emits_failed(monkeypatch) -> None:
    """الرد الفارغ أو المسافات يُعد فشلًا ولا يُحفظ."""
    socket = FakeWebSocket()
    _, env = _run(monkeypatch, _FakeGraph(response="   "), socket)
    assert [e["type"] for e in socket.events] == ["chat.started", "chat.failed"]
    env.messages.add.assert_not_awaited()


def test_run_chat_reply_save_failure_emits_failed(monkeypatch) -> None:
    """فشل حفظ الرد يُبلَّغ كفشل بدل إعلان اكتمال كاذب."""
    socket = FakeWebSocket()
    accepted = _accepted()
    env = _Env(monkeypatch, conversation=None)  # المحادثة اختفت قبل الحفظ
    owner, conv = str(accepted.user_id), str(accepted.conversation_id)
    active_chat_runs.try_begin(owner, conv)

    async def scenario() -> None:
        await chat_server.connect(owner, conv, socket)
        try:
            await run_chat(_FakeGraph(response="رد"), env.factory, accepted)
        finally:
            chat_server.disconnect(owner, conv, socket)

    asyncio.run(scenario())
    assert [e["type"] for e in socket.events] == ["chat.started", "chat.failed"]
    assert active_chat_runs.try_begin(owner, conv)


def test_run_chat_survives_client_disconnect(monkeypatch) -> None:
    """انقطاع المقبس أثناء التشغيل لا يرمي ولا يترك المحادثة محجوزة."""
    env = _Env(monkeypatch, conversation=Mock())
    accepted = _accepted()
    owner, conv = str(accepted.user_id), str(accepted.conversation_id)
    active_chat_runs.try_begin(owner, conv)
    asyncio.run(run_chat(_FakeGraph(response="رد"), env.factory, accepted))
    env.messages.add.assert_awaited_once()
    assert active_chat_runs.try_begin(owner, conv)
