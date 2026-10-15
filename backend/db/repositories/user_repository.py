"""مستودع المستخدمين."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


class UserRepository:
    """تنفيذ عمليات المستخدمين داخل جلسة قاعدة بيانات محقونة."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        role: str,
    ) -> User:
        """إنشاء مستخدم جديد ببريد مخفض (Lowercase)."""
        user = User(
            full_name=full_name,
            email=email.lower(),
            password_hash=password_hash,
            role=role,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_email(self, email: str) -> User | None:
        """جلب مستخدم ببريده الإلكتروني."""
        statement = select(User).where(User.email == email.lower())
        return await self._session.scalar(statement)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """جلب مستخدم بمعرفه."""
        statement = select(User).where(
            User.id == user_id,
            User.is_active == True,  # noqa: E712
        )
        return await self._session.scalar(statement)
