"""نموذج مقاطع المعرفة (Knowledge Chunks) للبحث الدلالي."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class KnowledgeChunk(Base):
    """قطعة معرفية: نص + تضمين متجه + بيانات وصفية للبحث الدلالي والنصي."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), default=None)
    subject: Mapped[str | None] = mapped_column(String(128), index=True, default=None)
    grade: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    chapter: Mapped[str | None] = mapped_column(String(128), default=None)
    source: Mapped[str | None] = mapped_column(String(255), index=True, default=None)
    metadata_: Mapped[dict | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_knowledge_chunks_subject_grade", "subject", "grade"),
    )
