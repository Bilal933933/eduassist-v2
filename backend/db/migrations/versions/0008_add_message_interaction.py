"""إضافة بطاقة استكمال البيانات إلى رسائل المساعد."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0008_add_message_interaction"
down_revision: str | Sequence[str] | None = "0007_add_message_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """إضافة عمود interaction اختياري لرسائل المساعد."""
    op.add_column(
        "messages",
        sa.Column("interaction", JSONB, nullable=True),
    )


def downgrade() -> None:
    """حذف عمود interaction من الرسائل."""
    op.drop_column("messages", "interaction")
