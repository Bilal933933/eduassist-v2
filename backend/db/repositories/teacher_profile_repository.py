"""مستودع بروفايل المعلم."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TeacherProfile


class TeacherProfileRepository:
    """قراءة بروفايل المعلم وإنشاؤه أو تحديثه داخل جلسة محقونة."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user(self, user_id: UUID) -> TeacherProfile | None:
        """جلب بروفايل المعلم بمعرف المستخدم أو لا شيء."""
        statement = select(TeacherProfile).where(
            TeacherProfile.user_id == user_id
        )
        return await self._session.scalar(statement)

    async def upsert(
        self,
        user_id: UUID,
        subject: str,
        class_name: str,
        students_note: str,
    ) -> TeacherProfile:
        """إنشاء البروفايل أو تحديث حقوله عند وجوده."""
        profile = await self.get_by_user(user_id)
        if profile is None:
            profile = TeacherProfile(
                user_id=user_id,
                subject=subject,
                class_name=class_name,
                students_note=students_note,
            )
            self._session.add(profile)
        else:
            profile.subject = subject
            profile.class_name = class_name
            profile.students_note = students_note
        await self._session.flush()
        return profile
