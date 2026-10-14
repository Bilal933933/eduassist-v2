"""إنشاء جدول المحادثات المملوكة للمستخدمين."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_create_conversations"
down_revision: str | Sequence[str] | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إنشاء جدول المحادثات وقيود ملكيته."""
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_conversations_status",
        ),
    )
    op.create_index(
        "ix_conversations_user_updated",
        "conversations",
        ["user_id", "updated_at"],
    )


def downgrade() -> None:
    """حذف جدول المحادثات عند التراجع عن الترحيل."""
    op.drop_index("ix_conversations_user_updated", table_name="conversations")
    op.drop_table("conversations")
