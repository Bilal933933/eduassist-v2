"""اختبارات خدمة المصادقة بعزل قاعدة البيانات."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from services.auth_service import (
    AccountInactiveError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidRoleError,
    get_user_by_token,
    login_user,
    logout_user,
    register_user,
)


def _session_with(user=None, session_row=None) -> Mock:
    """جلسة وهمية ترد بكائنات جاهزة حسب نوع الاستعلام."""
    from db.models import AuthSession, User

    session = Mock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()

    async def fake_scalar(statement) -> object | None:
        entity = statement.column_descriptions[0]["entity"]
        if entity is User:
            return user
        if entity is AuthSession:
            return session_row
        return None

    session.scalar = AsyncMock(side_effect=fake_scalar)
    return session


def test_register_creates_user_and_returns_raw_token() -> None:
    """التسجيل ينشئ مستخدمًا ويعيد رمزًا خامًا."""
    session = _session_with(user=None)
    user, raw_token = asyncio.run(
        register_user(session, "مدرس", "t@example.com", "كلمة-قوية-123", "teacher")
    )
    assert raw_token
    assert session.add.call_count == 2  # مستخدم + جلسة


def test_register_rejects_duplicate_email() -> None:
    """البريد المكرر يُرفض."""
    existing = Mock()
    session = _session_with(user=existing)
    with pytest.raises(EmailAlreadyExistsError):
        asyncio.run(
            register_user(session, "مدرس", "t@example.com", "كلمة-قوية-123", "teacher")
        )


def test_register_rejects_admin_role() -> None:
    """دور المدير مرفوض في التسجيل العام."""
    session = _session_with(user=None)
    with pytest.raises(InvalidRoleError):
        asyncio.run(
            register_user(session, "مدير", "a@example.com", "كلمة-قوية-123", "admin")
        )


def test_login_rejects_wrong_password() -> None:
    """كلمة خاطئة تُرفض عند الدخول."""
    from security.passwords import hash_password

    user = Mock()
    user.password_hash = hash_password("الصحيحة-123")
    session = _session_with(user=user)
    with pytest.raises(InvalidCredentialsError):
        asyncio.run(login_user(session, "t@example.com", "الخاطئة-456"))


def test_login_rejects_inactive_account() -> None:
    """الحساب الموقوف يُرفض بخطأ مستقل."""
    from security.passwords import hash_password

    user = Mock()
    user.password_hash = hash_password("الصحيحة-123")
    user.is_active = False
    session = _session_with(user=user)
    with pytest.raises(AccountInactiveError):
        asyncio.run(login_user(session, "t@example.com", "الصحيحة-123"))


def test_get_user_by_token_returns_none_without_session() -> None:
    """رمز بلا جلسة صالحة يعيد لا شيء."""
    session = _session_with(user=None, session_row=None)
    assert asyncio.run(get_user_by_token(session, "خام-بلا-جلسة")) is None


def test_logout_revokes_session_by_hash() -> None:
    """الخروج ينفذ تحديث إبطال باستخدام تجزئة الرمز."""
    session = _session_with()
    raw = "رمز-للخروج"
    asyncio.run(logout_user(session, raw))
    session.execute.assert_awaited_once()
    statement = session.execute.await_args.args[0]
    assert "UPDATE auth_sessions" in str(statement)
    assert "revoked_at" in str(statement)


def test_expired_session_is_not_valid() -> None:
    """استعلام الجلسة الصالحة يشترط عدم الانتهاء وعدم الإبطال."""
    from db.repositories import AuthSessionRepository

    session = _session_with(session_row=None)
    result = asyncio.run(AuthSessionRepository(session).get_valid("token-hash"))
    assert result is None
    statement = session.scalar.await_args.args[0]
    sql = str(statement)
    assert "auth_sessions.expires_at >" in sql
    assert "auth_sessions.revoked_at IS NULL" in sql
