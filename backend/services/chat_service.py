"""خدمة المحادثة: قبول الرسالة فورًا ثم تشغيل الرسم في الخلفية وإصدار أحداثه."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TeacherProfile
from db.repositories import (
    ConversationRepository,
    MessageRepository,
    TeacherProfileRepository,
)
from db.session import SessionFactory
from graph import checkpoint_config
from realtime.chat_server import chat_server
from services.chat_runs import active_chat_runs
from services.errors import (
    ChatBusyError,
    ConversationNotFoundError,
    EventConnectionRequiredError,
)
from shared.context_builder import build_classifier_view, build_generator_view

logger = logging.getLogger("eduassist.chat")

CHAT_FAILED_CODE = "CHAT_FAILED"
CHAT_FAILED_MESSAGE = "تعذر إكمال المحادثة."

# إعادة التصدير للتوافق مع المستوردين الحاليين.
__all__ = [
    "AcceptedChat",
    "ChatBusyError",
    "ConversationNotFoundError",
    "EventConnectionRequiredError",
    "accept_chat",
    "create_conversation",
    "run_chat",
]


@dataclass(frozen=True, slots=True)
class AcceptedChat:
    """رسالة مقبولة ومحفوظة وجاهزة لتشغيل الرسم في الخلفية."""

    user_id: UUID
    conversation_id: UUID
    message: str
    user_role: str
    context: dict[str, Any]


def build_teacher_brief(profile: TeacherProfile | None) -> str:
    """خلاصة مضغوطة لبيانات المعلم تصلح للحقن في السياق."""
    if profile is None:
        return ""
    return (
        f"المادة: {profile.subject}، الصف: {profile.class_name}، "
        f"الطلاب: {profile.students_note}"
    )[:200]


async def accept_chat(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    message: str,
    user_role: str = "student",
) -> AcceptedChat:
    """التحقق من الشروط وحفظ رسالة المستخدم وحجز التشغيل (المرحلة المتزامنة)."""
    if user_role not in ("teacher", "student"):
        user_role = "student"
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

    if not active_chat_runs.try_begin(owner_key, conversation_key):
        raise ChatBusyError
    try:
        messages = MessageRepository(session)
        prior_rows = await messages.list_recent(conversation_id, user_id)
        generator_view = build_generator_view(prior_rows)
        context: dict[str, Any] = {
            "history": generator_view["history"],
            "classifier_view": build_classifier_view(prior_rows),
            "generator_view": generator_view,
        }
        if user_role == "teacher":
            profile = await TeacherProfileRepository(session).get_by_user(user_id)
            teacher_brief = build_teacher_brief(profile)
            if teacher_brief:
                context["teacher_brief"] = teacher_brief
        await messages.add(conversation_id, user_id, "user", message)
        conversation.updated_at = datetime.now(timezone.utc)
        await session.commit()
    except BaseException:
        # فشل القبول لا يجوز أن يترك المحادثة محجوزة.
        active_chat_runs.end(owner_key, conversation_key)
        raise
    return AcceptedChat(user_id, conversation_id, message, user_role, context)


async def run_chat(
    graph: Any,
    session_factory: SessionFactory,
    accepted: AcceptedChat,
) -> None:
    """تشغيل الرسم وحفظ الرد وإصدار الأحداث (المرحلة الخلفية، لا ترمي أبدًا)."""
    owner_key = str(accepted.user_id)
    conversation_key = str(accepted.conversation_id)
    try:
        await chat_server.send_started(owner_key, conversation_key)
        response = await _collect_response(graph, accepted)
        if response is None:
            logger.error("انتهى الرسم دون رد للمحادثة %s", conversation_key)
            await _send_failed(owner_key, conversation_key)
            return
        await _save_assistant_reply(session_factory, accepted, response)
        await chat_server.send_completed(owner_key, conversation_key, response)
    except Exception:
        # رسالة المستخدم محفوظة مسبقًا: الفشل يُبلَّغ عبر المقبس فقط.
        logger.exception("فشل تشغيل المحادثة %s", conversation_key)
        await _send_failed(owner_key, conversation_key)
    finally:
        active_chat_runs.end(owner_key, conversation_key)


async def _collect_response(graph: Any, accepted: AcceptedChat) -> str | None:
    """بث أحداث الرسم واستخراج آخر رد نصي."""
    owner_key = str(accepted.user_id)
    event_stream = graph.astream_events(
        {
            "messages": [accepted.message],
            "user_id": owner_key,
            "user_role": accepted.user_role,
            "context": accepted.context,
        },
        checkpoint_config(owner_key, str(accepted.conversation_id)),
        version="v2",
    )
    response: str | None = None
    async for event in event_stream:
        if event.get("event") != "on_chain_end":
            continue
        output = event.get("data", {}).get("output", {})
        if isinstance(output, dict) and isinstance(output.get("response"), str):
            response = output["response"]
    return response


async def _save_assistant_reply(
    session_factory: SessionFactory,
    accepted: AcceptedChat,
    response: str,
) -> None:
    """حفظ رد المساعد بجلسة مستقلة عن جلسة الطلب المنتهية."""
    async with session_factory() as session:
        conversation = await ConversationRepository(session).get_owned(
            accepted.conversation_id,
            accepted.user_id,
        )
        if conversation is None:
            raise ConversationNotFoundError
        await MessageRepository(session).add(
            accepted.conversation_id,
            accepted.user_id,
            "assistant",
            response,
        )
        conversation.updated_at = datetime.now(timezone.utc)
        await session.commit()


async def _send_failed(owner_key: str, conversation_key: str) -> None:
    """إرسال حدث الفشل العام دون تفاصيل داخلية."""
    await chat_server.send_failed(
        owner_key, conversation_key, CHAT_FAILED_CODE, CHAT_FAILED_MESSAGE
    )


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
