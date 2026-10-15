"""إكمال حقول وفهارس جلسات المصادقة."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_complete_auth_sessions"
down_revision: str | Sequence[str] | None = "0004_create_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إضافة وقت الإبطال وفهرس تنظيف الجلسات المنتهية."""
    op.add_column(
        "auth_sessions",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_auth_sessions_expires_at",
        "auth_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    """إزالة إضافات إكمال جلسات المصادقة."""
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_column("auth_sessions", "revoked_at")
