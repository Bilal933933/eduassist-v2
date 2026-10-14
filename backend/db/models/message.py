"""نموذج رسالة داخل محادثة."""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.conversation import Conversation


class Message(Base):
    """رسالة يرسلها المستخدم أو المساعد داخل محادثة مملوكة للمستخدم."""

    __tablename__ = "messages"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["conversation_id", "user_id"],
            ["conversations.id", "conversations.user_id"],
            name="fk_messages_conversation_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "sender IN ('user', 'assistant')",
            name="ck_messages_sender",
        ),
        sa.Index(
            "ix_messages_conversation_sequence",
            "conversation_id",
            "sequence_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        sa.Uuid(),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    conversation_id: Mapped[UUID] = mapped_column(sa.Uuid(), nullable=False)
    user_id: Mapped[UUID] = mapped_column(sa.Uuid(), nullable=False)
    sender: Mapped[str] = mapped_column(sa.String(length=16), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    sequence_number: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.Identity(),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
