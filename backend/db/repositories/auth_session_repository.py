"""مستودع جلسات المصادقة."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuthSession


class AuthSessionRepository:
    """تنفيذ عمليات الجلسات داخل جلسة قاعدة بيانات محقونة."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> AuthSession:
        """إنشاء صف جلسة لتجزئة رمز (Token Hash) جديدة."""
        row = AuthSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_valid(self, token_hash: str) -> AuthSession | None:
        """جلب جلسة غير منتهية بتجزئة رمزها."""
        now = datetime.now(timezone.utc)
        statement = select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.expires_at > now,
            AuthSession.revoked_at.is_(None),
        )
        return await self._session.scalar(statement)

    async def revoke_by_hash(self, token_hash: str) -> None:
        """إبطال جلسة واحدة مع الاحتفاظ بسجلها."""
        await self._session.execute(
            update(AuthSession)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """إبطال جميع الجلسات النشطة لمستخدم."""
        await self._session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
