"""نموذج المستخدم متعدد الأدوار."""
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.auth_session import AuthSession
    from db.models.conversation import Conversation
    from db.models.teacher_profile import TeacherProfile


class User(Base):
    """حساب مستخدم للمصادقة وتحديد الدور."""

    __tablename__ = "users"
    __table_args__ = (
        sa.CheckConstraint(
            "role IN ('teacher', 'student', 'admin')",
            name="ck_users_role",
        ),
        sa.CheckConstraint(
            "email = lower(email)",
            name="ck_users_email_lowercase",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[UUID] = mapped_column(
        sa.Uuid(),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    full_name: Mapped[str] = mapped_column(sa.String(length=200))
    email: Mapped[str] = mapped_column(sa.String(length=320))
    password_hash: Mapped[str] = mapped_column(sa.Text())
    role: Mapped[str] = mapped_column(sa.String(length=32))
    is_active: Mapped[bool] = mapped_column(
        server_default=sa.true(),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    teacher_profile: Mapped["TeacherProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
