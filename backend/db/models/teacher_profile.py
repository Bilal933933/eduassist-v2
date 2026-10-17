"""نموذج بروفايل المعلم."""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.user import User


class TeacherProfile(Base):
    """بيانات المعلم الوصفية: المادة والصف ووصف الطلاب."""

    __tablename__ = "teacher_profiles"
    __table_args__ = (
        sa.UniqueConstraint("user_id", name="uq_teacher_profiles_user"),
    )

    id: Mapped[UUID] = mapped_column(
        sa.Uuid(),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(sa.String(length=100))
    class_name: Mapped[str] = mapped_column(sa.String(length=100))
    students_note: Mapped[str] = mapped_column(sa.Text())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="teacher_profile")
