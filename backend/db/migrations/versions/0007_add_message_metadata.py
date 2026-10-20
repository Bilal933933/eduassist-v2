"""إضافة عمود ميتا ديتا للرسائل لتتبّع مصدر الرد."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0007_add_message_metadata"
down_revision: str | Sequence[str] | None = "0006_create_teacher_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إضافة عمود metadata اختياري لرسائل المساعد."""
    op.add_column(
        "messages",
        sa.Column("metadata", JSONB, nullable=True),
    )


def downgrade() -> None:
    """حذف عمود metadata من الرسائل."""
    op.drop_column("messages", "metadata")
