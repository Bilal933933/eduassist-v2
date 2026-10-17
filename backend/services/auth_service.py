"""حالات استخدام المصادقة (تسجيل، دخول، خروج، مستخدم حالي)."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from db.repositories import AuthSessionRepository, UserRepository
from security.passwords import (
    burn_password_verification,
    hash_password,
    verify_and_update_password,
)
from security.session_tokens import generate_token, hash_token
from services.errors import (
    AccountInactiveError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidRoleError,
)

# ─── الأدوار المسموحة في التسجيل العام (المدير يُنشأ يدويًا خارج الواجهة) ───
ALLOWED_ROLES = {"teacher", "student"}

# إعادة التصدير للتوافق مع المستوردين الحاليين.
__all__ = [
    "AccountInactiveError",
    "EmailAlreadyExistsError",
    "InvalidCredentialsError",
    "InvalidRoleError",
    "get_user_by_token",
    "login_user",
    "logout_user",
    "register_user",
]


async def register_user(
    session: AsyncSession,
    full_name: str,
    email: str,
    password: str,
    role: str,
    session_days: int = 30,
) -> tuple[object, str]:
    """تسجيل مستخدم جديد وإنشاء جلسة أولى له."""
    if role not in ALLOWED_ROLES:
        raise InvalidRoleError
    users = UserRepository(session)
    if await users.get_by_email(email):
        raise EmailAlreadyExistsError
    try:
        user = await users.create(full_name, email, hash_password(password), role)
    except IntegrityError as exc:
        raise EmailAlreadyExistsError from exc
    raw_token = await _create_session(session, user.id, session_days)  # type: ignore[arg-type]
    return user, raw_token


async def login_user(
    session: AsyncSession,
    email: str,
    password: str,
    session_days: int = 30,
) -> tuple[object, str]:
    """التحقق من بيانات الدخول وإنشاء جلسة جديدة."""
    users = UserRepository(session)
    user = await users.get_by_email(email)
    if user is None:
        # زمن تحقق مماثل للحساب الموجود حتى لا يكشف الفرق الزمني وجود البريد.
        burn_password_verification(password)
        raise InvalidCredentialsError
    try:
        valid, updated_hash = verify_and_update_password(
            password,
            str(user.password_hash),  # type: ignore[attr-defined]
        )
    except (TypeError, ValueError):
        raise InvalidCredentialsError from None
    if not valid:
        raise InvalidCredentialsError
    # حالة الحساب لا تُكشف إلا لمن أثبت معرفة كلمة المرور الصحيحة.
    if not user.is_active:  # type: ignore[attr-defined]
        raise AccountInactiveError(user.id)  # type: ignore[arg-type]
    if updated_hash is not None:
        user.password_hash = updated_hash  # type: ignore[attr-defined]
    raw_token = await _create_session(session, user.id, session_days)  # type: ignore[arg-type]
    return user, raw_token


async def logout_user(session: AsyncSession, raw_token: str) -> None:
    """إبطال جلسة واحدة بتجزئة رمزها."""
    sessions = AuthSessionRepository(session)
    await sessions.revoke_by_hash(hash_token(raw_token))


async def get_user_by_token(
    session: AsyncSession,
    raw_token: str,
) -> object | None:
    """جلب المستخدم صاحب جلسة صالحة، أو لا شيء عند غيابها."""
    sessions = AuthSessionRepository(session)
    row = await sessions.get_valid(hash_token(raw_token))
    if row is None:
        return None
    users = UserRepository(session)
    return await users.get_by_id(row.user_id)


async def _create_session(
    session: AsyncSession,
    user_id: UUID,
    session_days: int,
) -> str:
    """إنشاء صف جلسة وإرجاع الرمز الخام مرة واحدة."""
    raw_token = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=session_days)
    sessions = AuthSessionRepository(session)
    await sessions.create(user_id, hash_token(raw_token), expires_at)
    return raw_token
