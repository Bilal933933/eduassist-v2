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
        metadata: dict | None = None,
        interaction: dict | None = None,
    ) -> Message:
        """إضافة رسالة مع مالك المحادثة وميتا داتا مصدر الرد."""
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            sender=sender,
            content=content,
            metadata_=metadata,
            interaction_=interaction,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def get_owned(
        self,
        message_id: UUID,
        conversation_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> Message | None:
        """جلب رسالة مملوكة، مع قفل الصف عند تعديل بطاقتها."""
        statement = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
            Message.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

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

    async def list_recent(
        self,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = 12,
    ) -> list[Message]:
        """جلب آخر رسائل المحادثة بحد من القاعدة لا من الذاكرة."""
        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.user_id == user_id,
            )
            .order_by(Message.sequence_number.desc())
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return list(reversed(list(result)))

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
