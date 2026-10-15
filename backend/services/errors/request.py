"""أخطاء الطلب الوارد (Request Errors)."""
from services.errors.base import AuthorizationError, ValidationError


class OriginNotAllowedError(AuthorizationError):
    """خطأ يدل على مصدر طلب غير مسموح."""

    code = "ORIGIN_NOT_ALLOWED"
    message = "مصدر الطلب غير مسموح."


class InvalidCursorError(ValidationError):
    """خطأ يدل على مؤشر ترقيم تالف أو غير صالح."""

    code = "INVALID_CURSOR"
    message = "مؤشر الصفحة غير صالح."
