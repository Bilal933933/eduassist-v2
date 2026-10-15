"""نموذج جلسة المصادقة (Auth Session)."""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.user import User


class AuthSession(Base):
    """صف جلسة واحد يربط المستخدم برمز مجزأ (Token Hash)."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        sa.Index("ix_auth_sessions_token_hash", "token_hash"),
        sa.Index("ix_auth_sessions_user_id", "user_id"),
        sa.Index("ix_auth_sessions_expires_at", "expires_at"),
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
    token_hash: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="auth_sessions")
