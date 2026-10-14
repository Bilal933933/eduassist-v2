"""إنشاء جدول الرسائل وربطه بمالك المحادثة."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_create_messages"
down_revision: str | Sequence[str] | None = "0002_create_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إنشاء جدول الرسائل وفرض تطابق مالكها مع مالك المحادثة."""
    op.create_unique_constraint(
        "uq_conversations_id_user",
        "conversations",
        ["id", "user_id"],
    )
    op.create_table(
        "messages",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("sender", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "sequence_number",
            sa.BigInteger(),
            sa.Identity(),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
    )
    op.create_index(
        "ix_messages_conversation_sequence",
        "messages",
        ["conversation_id", "sequence_number"],
    )


def downgrade() -> None:
    """حذف جدول الرسائل وقيد ملكية المحادثة."""
    op.drop_index("ix_messages_conversation_sequence", table_name="messages")
    op.drop_table("messages")
    op.drop_constraint(
        "uq_conversations_id_user",
        "conversations",
        type_="unique",
    )
