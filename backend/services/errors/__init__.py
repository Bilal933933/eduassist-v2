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
    RateLimitError,
    ValidationError,
)
from services.errors.conversations import (
    ChatBusyError,
    ConversationNotFoundError,
    EventConnectionRequiredError,
)
from services.errors.request import (
    InvalidCursorError,
    OriginNotAllowedError,
    RateLimitExceededError,
)

__all__ = [
    "AccountInactiveError",
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "ChatBusyError",
    "ConflictError",
    "ConversationNotFoundError",
    "EmailAlreadyExistsError",
    "EventConnectionRequiredError",
    "InvalidCredentialsError",
    "InvalidRoleError",
    "InvalidCursorError",
    "NotFoundError",
    "OriginNotAllowedError",
    "RateLimitError",
    "RateLimitExceededError",
    "SessionInvalidError",
    "ValidationError",
]

# كل الأصناف الملموسة للتسجيل الصريح في المعالج المركزي.
ALL_ERRORS: tuple[type[AppError], ...] = (
    AccountInactiveError,
    ChatBusyError,
    ConversationNotFoundError,
    EmailAlreadyExistsError,
    EventConnectionRequiredError,
    InvalidCredentialsError,
    InvalidCursorError,
    InvalidRoleError,
    NotFoundError,
    OriginNotAllowedError,
    RateLimitExceededError,
    SessionInvalidError,
)
