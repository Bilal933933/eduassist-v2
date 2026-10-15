"""اختبار تكامل المصادقة الحقيقي على PostgreSQL المحلية."""
import asyncio
import os
import selectors
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete

from config.settings import settings
from db.session import open_session_factory
from db.models import AuthSession, User
from security.session_tokens import hash_token
from services.auth_service import (
    AccountInactiveError,
    get_user_by_token,
    login_user,
    logout_user,
    register_user,
)


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_postgres_auth_register_login_revoke_roundtrip() -> None:
    """التسجيل والدخول والإبطال يعمل على القاعدة الحقيقية."""

    async def scenario() -> None:
        created_user_id: UUID | None = None
        async with open_session_factory(settings.DATABASE_URL) as session_factory:
            async with session_factory() as session:
                try:
                    email = f"auth-{uuid4().hex}@example.com"
                    user, first_token = await register_user(
                        session, "مستخدم مصادقة", email, "كلمة-قوية-123", "student"
                    )
                    created_user_id = user.id
                    await session.commit()
                    assert await get_user_by_token(session, first_token) is not None

                    await logout_user(session, first_token)
                    await session.commit()
                    assert await get_user_by_token(session, first_token) is None

                    same_user, _ = await login_user(
                        session, email, "كلمة-قوية-123"
                    )
                    await session.commit()
                    assert same_user.id == user.id
                finally:
                    await session.rollback()
                    if created_user_id is not None:
                        await session.execute(delete(User).where(User.id == created_user_id))
                        await session.commit()

    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(scenario())
    else:
        asyncio.run(scenario())


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_postgres_auth_rejects_wrong_password() -> None:
    """كلمة خاطئة تُرفض على القاعدة الحقيقية."""

    async def scenario() -> None:
        from services.errors import InvalidCredentialsError

        created_user_id: UUID | None = None
        async with open_session_factory(settings.DATABASE_URL) as session_factory:
            async with session_factory() as session:
                try:
                    email = f"auth-{uuid4().hex}@example.com"
                    user, _ = await register_user(
                        session, "مستخدم مصادقة", email, "كلمة-قوية-123", "student"
                    )
                    created_user_id = user.id
                    await session.commit()
                    with pytest.raises(InvalidCredentialsError):
                        await login_user(session, email, "كلمة-خاطئة-456")
                finally:
                    await session.rollback()
                    if created_user_id is not None:
                        await session.execute(delete(User).where(User.id == created_user_id))
                        await session.commit()

    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(scenario())
    else:
        asyncio.run(scenario())


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_postgres_auth_rejects_expired_session() -> None:
    """الجلسة المنتهية لا تعيد مستخدمًا من القاعدة الحقيقية."""

    async def scenario() -> None:
        created_user_id: UUID | None = None
        async with open_session_factory(settings.DATABASE_URL) as session_factory:
            async with session_factory() as session:
                try:
                    email = f"auth-{uuid4().hex}@example.com"
                    user, _ = await register_user(
                        session, "مستخدم مصادقة", email, "كلمة-قوية-123", "student"
                    )
                    created_user_id = user.id
                    raw_token = f"expired-{uuid4().hex}"
                    session.add(
                        AuthSession(
                            user_id=user.id,
                            token_hash=hash_token(raw_token),
                            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                        )
                    )
                    await session.commit()
                    assert await get_user_by_token(session, raw_token) is None
                finally:
                    await session.rollback()
                    if created_user_id is not None:
                        await session.execute(delete(User).where(User.id == created_user_id))
                        await session.commit()

    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(scenario())
    else:
        asyncio.run(scenario())
