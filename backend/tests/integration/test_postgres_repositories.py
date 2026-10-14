"""اختبار تكامل المستودعات مع PostgreSQL المحلية."""
import asyncio
import os
import selectors
import sys
from uuid import uuid4

import pytest

from config.settings import settings
from db.models import User
from db.repositories import ConversationRepository, MessageRepository
from db.session import open_session_factory


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_repositories_persist_owned_conversation_and_message() -> None:
    """تحفظ المستودعات المحادثة والرسالة للمالك نفسه."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as session_factory:
            async with session_factory() as session:
                try:
                    user = User(
                        full_name="مستخدم اختبار",
                        email=f"integration-{uuid4().hex}@example.com",
                        password_hash="test-only-hash",
                        role="student",
                    )
                    session.add(user)
                    await session.flush()

                    conversations = ConversationRepository(session)
                    messages = MessageRepository(session)
                    conversation = await conversations.create(user.id, "اختبار")
                    await messages.add(
                        conversation.id,
                        user.id,
                        "user",
                        "مرحبًا",
                    )

                    saved_messages = await messages.list_for_conversation(
                        conversation.id,
                        user.id,
                    )
                    assert [message.content for message in saved_messages] == [
                        "مرحبًا"
                    ]
                finally:
                    await session.rollback()

    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(scenario())
    else:
        asyncio.run(scenario())
