"""أخطاء المحادثات والأحداث (Conversations Errors)."""
from services.errors.base import ConflictError, NotFoundError


class ConversationNotFoundError(NotFoundError):
    """خطأ المحادثة الغائبة أو غير المملوكة برمز ورسالة ثابتين."""

    code = "CONVERSATION_NOT_FOUND"
    message = "المحادثة غير موجودة."

    def __init__(self) -> None:
        super().__init__("conversation", self.message)


class EventConnectionRequiredError(ConflictError):
    """خطأ يدل على غياب اتصال الأحداث المطلوب."""

    code = "EVENT_CONNECTION_REQUIRED"
    message = "يجب فتح اتصال الأحداث قبل إرسال الرسالة."
