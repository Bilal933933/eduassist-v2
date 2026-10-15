"""حزمة أخطاء التطبيق مقسمة حسب المجال (Domain)."""
from services.errors.auth import (
    AccountInactiveError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidRoleError,
    SessionInvalidError,
)
from services.errors.base import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from services.errors.conversations import (
    ConversationNotFoundError,
    EventConnectionRequiredError,
)
from services.errors.request import InvalidCursorError, OriginNotAllowedError

__all__ = [
    "AccountInactiveError",
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "ConversationNotFoundError",
    "EmailAlreadyExistsError",
    "EventConnectionRequiredError",
    "InvalidCredentialsError",
    "InvalidRoleError",
    "InvalidCursorError",
    "NotFoundError",
    "OriginNotAllowedError",
    "SessionInvalidError",
    "ValidationError",
]

# كل الأصناف الملموسة للتسجيل الصريح في المعالج المركزي.
ALL_ERRORS: tuple[type[AppError], ...] = (
    AccountInactiveError,
    ConversationNotFoundError,
    EmailAlreadyExistsError,
    EventConnectionRequiredError,
    InvalidCredentialsError,
    InvalidCursorError,
    InvalidRoleError,
    NotFoundError,
    OriginNotAllowedError,
    SessionInvalidError,
)
