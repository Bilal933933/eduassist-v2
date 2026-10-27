"""اختبارات حذف المحادثة بعزل المستودع عن قاعدة البيانات."""
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

import services.conversation_service as conversation_service
from services.conversation_service import delete_conversation
from services.errors import ConversationNotFoundError


def _fake_session() -> Mock:
    """جلسة وهمية تسجل التثبيت فقط."""
    session = Mock()
    session.commit = AsyncMock()
    return session


def test_delete_owned_conversation_commits(monkeypatch) -> None:
    """المحادثة المملوكة تُحذف ويُثبَّت الحذف مرة واحدة."""
    session = _fake_session()
    delete_owned = AsyncMock(return_value=True)
    monkeypatch.setattr(
        conversation_service.ConversationRepository,
        "delete_owned",
        delete_owned,
    )
    conversation_id = uuid4()
    user_id = uuid4()

    async def scenario() -> None:
        await delete_conversation(session, user_id, conversation_id)

    asyncio.run(scenario())
    delete_owned.assert_awaited_once_with(conversation_id, user_id)
    session.commit.assert_awaited_once()


def test_missing_or_unowned_conversation_raises_without_commit(monkeypatch) -> None:
    """غياب الصف يعني محادثة غائبة أو غير مملوكة: 404 بلا تثبيت."""
    session = _fake_session()
    monkeypatch.setattr(
        conversation_service.ConversationRepository,
        "delete_owned",
        AsyncMock(return_value=False),
    )

    async def scenario() -> None:
        with pytest.raises(ConversationNotFoundError):
            await delete_conversation(session, uuid4(), uuid4())

    asyncio.run(scenario())
    session.commit.assert_not_awaited()
