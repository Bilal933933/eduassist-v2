"""اختبار تكامل قائمة المحادثات والرسائل على PostgreSQL المحلية."""
import asyncio
import os
import selectors
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from config.settings import settings
from db.models import Conversation, Message, User
from db.repositories import ConversationRepository, MessageRepository
from db.session import open_session_factory
from services.conversation_service import (
    get_conversation_messages,
    list_conversations,
)
from services.errors import ConversationNotFoundError


def _run(scenario):  # type: ignore[no-untyped-def]
    """تشغيل سيناريو غير متزامن مع حلقة ويندوز عند الحاجة."""
    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(scenario())
    else:
        asyncio.run(scenario())


async def _make_user(session, role="student"):  # type: ignore[no-untyped-def]
    """إنشاء مستخدم اختبار ببريد فريد."""
    user = User(
        full_name="مستخدم اختبار",
        email=f"conv-{uuid4().hex}@example.com",
        password_hash="test-only-hash",
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_conversation(session, user_id, title, updated_at):  # type: ignore[no-untyped-def]
    """إنشاء محادثة بتاريخ تحديث محدد للتحكم في الترتيب."""
    conversation = Conversation(
        user_id=user_id, title=title, updated_at=updated_at
    )
    session.add(conversation)
    await session.flush()
    return conversation


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_list_returns_only_owner_in_recency_order() -> None:
    """القائمة تعيد محادثات المالك فقط من الأحدث."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as factory:
            async with factory() as session:
                try:
                    owner = await _make_user(session)
                    other = await _make_user(session)
                    base = datetime.now(timezone.utc)
                    first = await _make_conversation(
                        session, owner.id, "الأولى", base
                    )
                    second = await _make_conversation(
                        session, owner.id, "الثانية", base + timedelta(minutes=1)
                    )
                    third = await _make_conversation(
                        session, owner.id, "الثالثة", base + timedelta(minutes=2)
                    )
                    await _make_conversation(
                        session, other.id, "للآخر", base + timedelta(minutes=3)
                    )
                    items, next_cursor = await list_conversations(
                        session, owner.id, limit=50
                    )
                    assert [row.id for row in items] == [
                        third.id,
                        second.id,
                        first.id,
                    ]
                    assert next_cursor is None
                finally:
                    await session.rollback()

    _run(scenario)


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_messages_return_in_sequence_order() -> None:
    """رسائل المحادثة تعود بترتيب التسلسل."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as factory:
            async with factory() as session:
                try:
                    owner = await _make_user(session)
                    conversation = await _make_conversation(
                        session, owner.id, "ترتيب", datetime.now(timezone.utc)
                    )
                    messages = MessageRepository(session)
                    for index in range(5):
                        await messages.add(
                            conversation.id,
                            owner.id,
                            "user" if index % 2 == 0 else "assistant",
                            f"رسالة {index}",
                        )
                    rows, next_cursor = await get_conversation_messages(
                        session, owner.id, conversation.id, limit=50
                    )
                    assert [row.content for row in rows] == [
                        f"رسالة {index}" for index in range(5)
                    ]
                    sequences = [row.sequence_number for row in rows]
                    assert sequences == sorted(sequences)
                    assert next_cursor is None
                finally:
                    await session.rollback()

    _run(scenario)


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_cursor_walk_has_no_duplicates_or_loss() -> None:
    """المشي بالمؤشر يجمع كل العناصر بلا تكرار أو فقد."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as factory:
            async with factory() as session:
                try:
                    owner = await _make_user(session)
                    base = datetime.now(timezone.utc)
                    for index in range(5):
                        await _make_conversation(
                            session,
                            owner.id,
                            f"محادثة {index}",
                            base + timedelta(minutes=index),
                        )
                    collected = []
                    cursor = None
                    while True:
                        rows, cursor = await list_conversations(
                            session, owner.id, limit=2, cursor=cursor
                        )
                        collected.extend(row.id for row in rows)
                        if cursor is None:
                            break
                    assert len(collected) == 5
                    assert len(set(collected)) == 5

                    conversation = await _make_conversation(
                        session, owner.id, "رسائل", base
                    )
                    messages = MessageRepository(session)
                    for index in range(5):
                        await messages.add(
                            conversation.id, owner.id, "user", f"نص {index}"
                        )
                    seen = []
                    cursor = None
                    while True:
                        rows, cursor = await get_conversation_messages(
                            session, owner.id, conversation.id, limit=2, cursor=cursor
                        )
                        seen.extend(row.content for row in rows)
                        if cursor is None:
                            break
                    assert seen == [f"نص {index}" for index in range(5)]
                finally:
                    await session.rollback()

    _run(scenario)


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_delete_removes_conversation_and_messages() -> None:
    """حذف محادثة مملوكة يزيل رسائلها تلقائيًا عبر CASCADE."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as factory:
            async with factory() as session:
                try:
                    owner = await _make_user(session)
                    conversation = await _make_conversation(
                        session, owner.id, "للحذف", datetime.now(timezone.utc)
                    )
                    messages = MessageRepository(session)
                    await messages.add(conversation.id, owner.id, "user", "سؤال")
                    await messages.add(conversation.id, owner.id, "assistant", "جواب")
                    deleted = await ConversationRepository(session).delete_owned(
                        conversation.id, owner.id
                    )
                    assert deleted is True
                    remaining = await session.scalar(
                        select(func.count())
                        .select_from(Message)
                        .where(Message.conversation_id == conversation.id)
                    )
                    assert remaining == 0
                    assert (
                        await ConversationRepository(session).get_owned(
                            conversation.id, owner.id
                        )
                        is None
                    )
                finally:
                    await session.rollback()

    _run(scenario)


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_delete_of_other_user_conversation_is_refused() -> None:
    """محادثة مستخدم آخر لا تُحذف ولا تُكشف، والمحادثة باقية."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as factory:
            async with factory() as session:
                try:
                    owner = await _make_user(session)
                    other = await _make_user(session)
                    conversation = await _make_conversation(
                        session, owner.id, "محمية", datetime.now(timezone.utc)
                    )
                    deleted = await ConversationRepository(session).delete_owned(
                        conversation.id, other.id
                    )
                    assert deleted is False
                    assert (
                        await ConversationRepository(session).get_owned(
                            conversation.id, owner.id
                        )
                        is not None
                    )
                finally:
                    await session.rollback()

    _run(scenario)


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_other_user_messages_are_invisible() -> None:
    """رسائل مستخدم آخر تُرفض بنفس 404 ولا تظهر في قوائمه."""

    async def scenario() -> None:
        async with open_session_factory(settings.DATABASE_URL) as factory:
            async with factory() as session:
                try:
                    owner = await _make_user(session)
                    other = await _make_user(session)
                    conversation = await _make_conversation(
                        session, owner.id, "خاصة", datetime.now(timezone.utc)
                    )
                    await MessageRepository(session).add(
                        conversation.id, owner.id, "user", "سرية"
                    )
                    with pytest.raises(ConversationNotFoundError):
                        await get_conversation_messages(
                            session, other.id, conversation.id, limit=50
                        )
                    with pytest.raises(ConversationNotFoundError):
                        await get_conversation_messages(
                            session, other.id, uuid4(), limit=50
                        )
                    items, _ = await list_conversations(session, other.id, limit=50)
                    assert items == []
                finally:
                    await session.rollback()

    _run(scenario)
