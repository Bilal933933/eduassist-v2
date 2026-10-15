"""مستودع المحادثات."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
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

    async def list_owned_page(
        self,
        user_id: UUID,
        page_size: int,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Conversation]:
        """جلب صفحة محادثات المالك مرتبة من الأحدث (مؤشر مركب)."""
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(page_size)
        )
        if after is not None:
            after_updated_at, after_id = after
            statement = statement.where(
                tuple_(Conversation.updated_at, Conversation.id)
                < (after_updated_at, after_id)
            )
        result = await self._session.scalars(statement)
        return list(result)
