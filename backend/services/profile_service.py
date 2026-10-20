"""خدمة بروفايل المعلم: قراءة وضبط المادة والصف."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.teacher_profile import TeacherProfile
from db.repositories.teacher_profile_repository import TeacherProfileRepository
from services.errors import TeacherProfileForbiddenError


def _ensure_teacher(user_role: str) -> None:
    """رفض غير المعلم: بروفايل المعلم يخص مسار المعلم فقط."""
    if user_role != "teacher":
        raise TeacherProfileForbiddenError


async def get_profile(
    session: AsyncSession,
    user_id: UUID,
    user_role: str,
) -> TeacherProfile | None:
    """جلب بروفايل المعلم أو None إن لم يُضبط بعد."""
    _ensure_teacher(user_role)
    return await TeacherProfileRepository(session).get_by_user(user_id)


async def upsert_profile(
    session: AsyncSession,
    user_id: UUID,
    user_role: str,
    subject: str,
    class_name: str,
    students_note: str,
) -> TeacherProfile:
    """إنشاء بروفايل المعلم أو تحديث حقوله."""
    _ensure_teacher(user_role)
    return await TeacherProfileRepository(session).upsert(
        user_id, subject, class_name, students_note
    )
