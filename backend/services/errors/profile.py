"""أخطاء بروفايل المعلم."""
from services.errors.base import AuthorizationError


class TeacherProfileForbiddenError(AuthorizationError):
    """خطأ يدل على محاولة غير معلم ضبط بروفايل المعلم."""

    code = "TEACHER_PROFILE_FORBIDDEN"
    message = "بروفايل المعلم متاح للمعلم فقط."
