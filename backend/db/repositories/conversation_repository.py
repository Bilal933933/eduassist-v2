"""مستودع المحادثات."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Conversation


class ConversationRepository:
    """تنفيذ عمليات المحادثات داخل جلسة قاعدة بيانات محقونة."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        title: str | None = None,
    ) -> Conversation:
        """إنشاء محادثة جديدة لمستخدم."""
        conversation = Conversation(user_id=user_id, title=title)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get_owned(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversation | None:
        """جلب محادثة بشرط تطابق مالكها."""
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return await self._session.scalar(statement)
