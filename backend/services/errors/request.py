"""أخطاء الطلب الوارد (Request Errors)."""
from services.errors.base import AuthorizationError


class OriginNotAllowedError(AuthorizationError):
    """خطأ يدل على مصدر طلب غير مسموح."""

    code = "ORIGIN_NOT_ALLOWED"
    message = "مصدر الطلب غير مسموح."
