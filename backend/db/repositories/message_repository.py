"""مستودع الرسائل."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Message


class MessageRepository:
    """تنفيذ عمليات الرسائل داخل جلسة قاعدة بيانات محقونة."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        conversation_id: UUID,
        user_id: UUID,
        sender: str,
        content: str,
    ) -> Message:
        """إضافة رسالة مع مالك المحادثة."""
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            sender=sender,
            content=content,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_for_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> list[Message]:
        """جلب رسائل محادثة مملوكة للمستخدم بترتيبها."""
        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.user_id == user_id,
            )
            .order_by(Message.sequence_number)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def list_page_after(
        self,
        conversation_id: UUID,
        user_id: UUID,
        page_size: int,
        after_sequence: int | None = None,
    ) -> list[Message]:
        """جلب صفحة رسائل بعد مؤشر تسلسلي مع شرط الملكية المزدوج."""
        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.user_id == user_id,
            )
            .order_by(Message.sequence_number)
            .limit(page_size)
        )
        if after_sequence is not None:
            statement = statement.where(Message.sequence_number > after_sequence)
        result = await self._session.scalars(statement)
        return list(result)
