"""${message}

معرّف الترحيل: ${up_revision}
الترحيل السابق: ${down_revision | comma,n}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """تطبيق الترحيل."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """التراجع عن الترحيل."""
    ${downgrades if downgrades else "pass"}
