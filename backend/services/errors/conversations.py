"""أخطاء المحادثات والأحداث (Conversations Errors)."""
from services.errors.base import ConflictError


class EventConnectionRequiredError(ConflictError):
    """خطأ يدل على غياب اتصال الأحداث المطلوب."""

    code = "EVENT_CONNECTION_REQUIRED"
    message = "يجب فتح اتصال الأحداث قبل إرسال الرسالة."
