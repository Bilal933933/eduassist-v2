"""أساس أخطاء التطبيق (Application Errors)."""
from typing import ClassVar


class AppError(Exception):
    """أساس أخطاء التطبيق المعروفة.

    كل خطأ يحمل رمزه الثابت ورسالته العربية فقط، بينما تبقى تفاصيل
    بروتوكول HTTP داخل طبقة الواجهة البرمجية.
    """

    code: ClassVar[str] = "APP_ERROR"
    message: ClassVar[str] = "طلب غير صالح."


class ValidationError(AppError):
    """أساس أخطاء بيانات التطبيق غير الصالحة."""


class ConflictError(AppError):
    """أساس أخطاء تعارض حالة المورد أو الطلب."""


class AuthenticationError(AppError):
    """أساس أخطاء غياب المصادقة أو عدم صلاحيتها."""


class AuthorizationError(AppError):
    """أساس أخطاء رفض الصلاحية بعد معرفة هوية المستخدم."""


# ─── أسماء الموارد بالعربية لاشتقاق الرسائل ───
RESOURCE_NAMES: dict[str, str] = {
    "conversation": "المحادثة",
    "message": "الرسالة",
    "session": "الجلسة",
    "user": "المستخدم",
}


class NotFoundError(AppError):
    """خطأ غياب عام: يستقبل المورد ويشتق الرمز والرسالة منه.

    مثال: NotFoundError("conversation") ← الرمز CONVERSATION_NOT_FOUND.
    """

    code = "RESOURCE_NOT_FOUND"

    def __init__(self, resource: str = "resource", message: str | None = None) -> None:
        self.resource = resource
        self.code = f"{resource.upper()}_NOT_FOUND"
        self.message = message or f"{RESOURCE_NAMES.get(resource, 'المورد')} غير موجود."
        super().__init__(self.message)
