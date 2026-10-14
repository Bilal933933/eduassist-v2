"""اختبارات مستودعات المحادثات والرسائل."""
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from db.repositories import ConversationRepository, MessageRepository


def test_conversation_repository_adds_owned_conversation() -> None:
    """ينشئ المستودع محادثة تحمل معرّف مالكها."""
    session = Mock()
    session.flush = AsyncMock()
    repository = ConversationRepository(session)
    user_id = uuid4()

    conversation = asyncio.run(repository.create(user_id, "محادثة جديدة"))

    session.add.assert_called_once_with(conversation)
    session.flush.assert_awaited_once()
    assert conversation.user_id == user_id
    assert conversation.title == "محادثة جديدة"


def test_message_repository_adds_owned_message() -> None:
    """ينشئ المستودع رسالة تحمل المحادثة ومالكها."""
    session = Mock()
    session.flush = AsyncMock()
    repository = MessageRepository(session)
    conversation_id = uuid4()
    user_id = uuid4()

    message = asyncio.run(
        repository.add(
            conversation_id,
            user_id,
            "user",
            "مرحبًا",
        )
    )

    session.add.assert_called_once_with(message)
    session.flush.assert_awaited_once()
    assert message.conversation_id == conversation_id
    assert message.user_id == user_id
    assert message.content == "مرحبًا"
