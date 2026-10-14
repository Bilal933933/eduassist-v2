"""نموذج المحادثة بين المستخدم والمساعد."""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.message import Message
    from db.models.user import User


class Conversation(Base):
    """محادثة يملكها مستخدم واحد ويتفاعل فيها مع المساعد."""

    __tablename__ = "conversations"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_conversations_status",
        ),
        sa.Index("ix_conversations_user_updated", "user_id", "updated_at"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_conversations_id_user",
        ),
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
    title: Mapped[str | None] = mapped_column(sa.String(length=200))
    status: Mapped[str] = mapped_column(
        sa.String(length=16),
        server_default=sa.text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.sequence_number",
    )
