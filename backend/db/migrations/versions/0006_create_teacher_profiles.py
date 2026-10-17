"""إنشاء جدول بروفايل المعلم."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_create_teacher_profiles"
down_revision: str | Sequence[str] | None = "0005_complete_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إنشاء جدول بروفايل المعلم بملكية المستخدم."""
    op.create_table(
        "teacher_profiles",
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
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("class_name", sa.String(length=100), nullable=False),
        sa.Column("students_note", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("user_id", name="uq_teacher_profiles_user"),
    )


def downgrade() -> None:
    """حذف جدول بروفايل المعلم عند التراجع عن الترحيل."""
    op.drop_table("teacher_profiles")
