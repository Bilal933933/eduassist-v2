"""خدمة تشغيل رسم المحادثة وحفظ رسائله وإصدار أحداثه."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import ConversationRepository, MessageRepository
from graph import checkpoint_config
from realtime.chat_server import chat_server
from services.errors import ConversationNotFoundError, EventConnectionRequiredError

# إعادة التصدير للتوافق مع المستوردين الحاليين.
__all__ = [
    "ConversationNotFoundError",
    "EventConnectionRequiredError",
    "create_conversation",
    "process_chat",
]


async def process_chat(
    graph: Any,
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    message: str,
) -> None:
    """حفظ الرسالة وتشغيل الرسم وحفظ الرد وإصدار الأحداث."""
    owner_key = str(user_id)
    conversation_key = str(conversation_id)
    if not chat_server.is_connected(owner_key, conversation_key):
        raise EventConnectionRequiredError

    conversation = await ConversationRepository(session).get_owned(
        conversation_id,
        user_id,
    )
    if conversation is None:
        raise ConversationNotFoundError

    messages = MessageRepository(session)
    await messages.add(conversation_id, user_id, "user", message)
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()

    await chat_server.send_started(owner_key, conversation_key)
    try:
        event_stream = graph.astream_events(
            {"messages": [message], "user_id": owner_key},
            checkpoint_config(owner_key, conversation_key),
            version="v2",
        )
        response: str | None = None
        async for event in event_stream:
            if event.get("event") != "on_chain_end":
                continue
            output = event.get("data", {}).get("output", {})
            if isinstance(output, dict) and isinstance(output.get("response"), str):
                response = output["response"]
    except Exception:
        await chat_server.send_failed(
            owner_key, conversation_key, "CHAT_FAILED", "تعذر إكمال المحادثة."
        )
        raise

    if response is None:
        await chat_server.send_failed(
            owner_key, conversation_key, "CHAT_FAILED", "تعذر إكمال المحادثة."
        )
        raise RuntimeError("لم يصدر الرسم ردًا نهائيًا.")

    await messages.add(conversation_id, user_id, "assistant", response)
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await chat_server.send_completed(owner_key, conversation_key, response)


async def create_conversation(
    session: AsyncSession,
    user_id: UUID,
    title: str | None,
) -> object:
    """إنشاء محادثة مملوكة للمستخدم داخل حالة استخدام مستقلة."""
    normalized_title = title.strip() if title else None
    conversation = await ConversationRepository(session).create(
        user_id,
        normalized_title or None,
    )
    await session.commit()
    return conversation
