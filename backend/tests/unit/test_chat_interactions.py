"""اختبارات قبول إجابات البطاقة وإهمالها في خدمة المحادثة."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

import services.chat_service as chat_service
from orchestration.interactions.schema import Interaction
from realtime.chat_server import chat_server
from services.chat_runs import active_chat_runs
from services.chat_service import accept_chat
from services.errors import (
    InteractionAnswersInvalidError,
    InteractionClosedError,
    InteractionNotFoundError,
)


def _interaction() -> Interaction:
    return Interaction(
        intent="lesson_prep",
        properties={"topic": "Present Simple"},
        questions=[
            {
                "slot": "grade",
                "prompt": "لأي صف تريد هذه الخطة؟",
                "options": [{"label": "الأول الثانوي", "value": "الأول الثانوي"}],
            }
        ],
    )


def _env(monkeypatch: pytest.MonkeyPatch, interaction: Interaction | None):
    session = Mock()
    session.commit = AsyncMock()
    row = SimpleNamespace(
        sender="assistant",
        interaction_=(
            interaction.model_dump(mode="json") if interaction is not None else None
        ),
    )
    messages = Mock()
    messages.list_recent = AsyncMock(return_value=[])
    messages.add = AsyncMock()
    messages.get_owned = AsyncMock(return_value=row if interaction is not None else None)
    conversations = Mock()
    conversations.get_owned = AsyncMock(return_value=Mock())
    monkeypatch.setattr(chat_service, "MessageRepository", lambda s: messages)
    monkeypatch.setattr(
        chat_service,
        "ConversationRepository",
        lambda s: conversations,
    )

    @asynccontextmanager
    async def factory():  # type: ignore[no-untyped-def]
        yield session

    return SimpleNamespace(
        session=session,
        messages=messages,
        row=row,
        factory=factory,
    )


def _scenario(user_id, conversation_id, callback):  # type: ignore[no-untyped-def]
    socket = chat_server

    async def run():
        from tests.conftest import FakeWebSocket

        ws = FakeWebSocket()
        await socket.connect(str(user_id), str(conversation_id), ws)
        try:
            return await callback()
        finally:
            socket.disconnect(str(user_id), str(conversation_id), ws)
            active_chat_runs.end(str(user_id), str(conversation_id))

    return asyncio.run(run())


def test_accept_answer_resumes_with_merged_properties(monkeypatch) -> None:
    """الإجابة تُدمج مع خصائص البطاقة وتُحفظ كرسالة مرئية."""
    interaction = _interaction()
    env = _env(monkeypatch, interaction)
    user_id, conversation_id = uuid4(), uuid4()

    async def callback():
        return await accept_chat(
            env.session,
            user_id,
            conversation_id,
            "",
            "student",
            interaction_id=uuid4(),
            answers={"grade": "الأول الثانوي"},
            action="answer",
        )

    accepted = _scenario(user_id, conversation_id, callback)

    assert accepted.run is True
    assert accepted.context["interaction_resume"]["intent"] == "lesson_prep"
    assert accepted.context["interaction_resume"]["properties"] == {
        "topic": "Present Simple",
        "grade": "الأول الثانوي",
    }
    assert "الأول الثانوي" in accepted.message
    env.messages.add.assert_awaited_once_with(
        conversation_id,
        user_id,
        "user",
        accepted.message,
    )
    assert Interaction.model_validate(env.row.interaction_).status == "answered"


def test_accept_dismiss_closes_interaction_without_run(monkeypatch) -> None:
    """الإهمال يغلق البطاقة ولا يحجز تشغيلًا ولا يضيف رسالة."""
    interaction = _interaction()
    env = _env(monkeypatch, interaction)
    user_id, conversation_id = uuid4(), uuid4()

    async def callback():
        return await accept_chat(
            env.session,
            user_id,
            conversation_id,
            "",
            "student",
            interaction_id=uuid4(),
            action="dismiss",
        )

    accepted = _scenario(user_id, conversation_id, callback)

    assert accepted.run is False
    env.messages.add.assert_not_awaited()
    assert Interaction.model_validate(env.row.interaction_).status == "dismissed"
    assert active_chat_runs.try_begin(str(user_id), str(conversation_id))


def test_accept_rejects_missing_required_answer(monkeypatch) -> None:
    """الإجابة الناقصة تُرفض وتحرر حجز التشغيل."""
    interaction = _interaction()
    env = _env(monkeypatch, interaction)
    user_id, conversation_id = uuid4(), uuid4()

    async def callback():
        with pytest.raises(InteractionAnswersInvalidError):
            await accept_chat(
                env.session,
                user_id,
                conversation_id,
                "",
                "student",
                interaction_id=uuid4(),
                answers={},
                action="answer",
            )

    _scenario(user_id, conversation_id, callback)
    assert active_chat_runs.try_begin(str(user_id), str(conversation_id))


def test_accept_rejects_closed_interaction(monkeypatch) -> None:
    """لا تُقبل إجابة بطاقة مغلقة."""
    interaction = _interaction().model_copy(update={"status": "dismissed"})
    env = _env(monkeypatch, interaction)
    user_id, conversation_id = uuid4(), uuid4()

    async def callback():
        with pytest.raises(InteractionClosedError):
            await accept_chat(
                env.session,
                user_id,
                conversation_id,
                "",
                "student",
                interaction_id=uuid4(),
                answers={"grade": "الأول الثانوي"},
                action="answer",
            )

    _scenario(user_id, conversation_id, callback)


def test_accept_rejects_unknown_interaction(monkeypatch) -> None:
    """البطاقة غير المملوكة أو غير الموجودة تُرفض."""
    env = _env(monkeypatch, None)
    user_id, conversation_id = uuid4(), uuid4()

    async def callback():
        with pytest.raises(InteractionNotFoundError):
            await accept_chat(
                env.session,
                user_id,
                conversation_id,
                "",
                "student",
                interaction_id=uuid4(),
                answers={"grade": "الأول الثانوي"},
                action="answer",
            )

    _scenario(user_id, conversation_id, callback)
