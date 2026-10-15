"""أخطاء المصادقة (Authentication Errors)."""
from uuid import UUID

from services.errors.base import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ValidationError,
)


class EmailAlreadyExistsError(ConflictError):
    """خطأ يدل على تكرار البريد الإلكتروني."""

    code = "EMAIL_TAKEN"
    message = "البريد الإلكتروني مسجل بالفعل."


class InvalidCredentialsError(AuthenticationError):
    """خطأ يدل على بريد أو كلمة مرور غير صحيحة."""

    code = "INVALID_CREDENTIALS"
    message = "البريد أو كلمة المرور غير صحيحة."


class AccountInactiveError(AuthorizationError):
    """خطأ يدل على حساب موقوف."""

    code = "ACCOUNT_INACTIVE"
    message = "الحساب موقوف. تواصل مع الإدارة."

    def __init__(self, user_id: UUID | None = None) -> None:
        self.user_id = user_id
        super().__init__(self.message)


class InvalidRoleError(ValidationError):
    """خطأ يدل على دور غير مسموح."""

    code = "ROLE_NOT_ALLOWED"
    message = "الدور غير مسموح."


class SessionInvalidError(AuthenticationError):
    """خطأ يدل على جلسة غائبة أو منتهية أو مبطلة."""

    code = "SESSION_INVALID"
    message = "الجلسة غير صالحة أو منتهية."
