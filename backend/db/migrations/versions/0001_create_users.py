"""إنشاء جدول المستخدمين متعدد الأدوار."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_users"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إنشاء جدول المستخدمين وقيوده."""
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
            "role IN ('teacher', 'student', 'admin')",
            name="ck_users_role",
        ),
        sa.CheckConstraint(
            "email = lower(email)",
            name="ck_users_email_lowercase",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )


def downgrade() -> None:
    """حذف جدول المستخدمين عند التراجع عن الترحيل."""
    op.drop_table("users")
