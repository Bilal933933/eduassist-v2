"""أخطاء المحادثات والأحداث (Conversations Errors)."""
from services.errors.base import ConflictError, NotFoundError, ValidationError


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


class ChatBusyError(ConflictError):
    """خطأ يدل على أن المحادثة ما زالت تعالج رسالة سابقة."""

    code = "CHAT_BUSY"
    message = "المساعد ما زال يعالج رسالتك السابقة."


class InteractionNotFoundError(NotFoundError):
    """بطاقة استكمال البيانات غير موجودة أو غير مملوكة."""

    code = "INTERACTION_NOT_FOUND"
    message = "بطاقة الأسئلة غير موجودة."

    def __init__(self) -> None:
        super().__init__("interaction", self.message)


class InteractionClosedError(ConflictError):
    """محاولة إجابة بطاقة سبق إغلاقها."""

    code = "INTERACTION_CLOSED"
    message = "تمت الإجابة على هذه البطاقة أو إغلاقها مسبقًا."


class InteractionAnswersInvalidError(ValidationError):
    """إجابات لا تطابق أسئلة البطاقة."""

    code = "INTERACTION_ANSWERS_INVALID"
    message = "الإجابات المرسلة لا تطابق أسئلة البطاقة."
