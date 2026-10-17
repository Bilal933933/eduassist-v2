"""مستودع مقاطع المعرفة: إدراج وبحث دلالي ونصي."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.knowledge import KnowledgeChunk


class KnowledgeRepository:
    """عمليات مقاطع المعرفة داخل جلسة قاعدة بيانات محقونة."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_chunk(
        self,
        content: str,
        embedding: list[float],
        subject: str | None = None,
        grade: str | None = None,
        chapter: str | None = None,
        source: str | None = None,
        metadata_: dict | None = None,
    ) -> KnowledgeChunk:
        """إدراج قطعة معرفية واحدة وإرجاعها بعدflush."""
        chunk = KnowledgeChunk(
            content=content,
            embedding=embedding,
            subject=subject,
            grade=grade,
            chapter=chapter,
            source=source,
            metadata_=metadata_,
        )
        self._session.add(chunk)
        await self._session.flush()
        return chunk

    async def add_chunks_batch(self, chunks: list[dict[str, Any]]) -> None:
        """إدراج دفعة من القطع المعرفية دفعة واحدة."""
        objs = [KnowledgeChunk(**c) for c in chunks]
        self._session.add_all(objs)
        await self._session.flush()

    async def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 5,
        subject: str | None = None,
        grade: str | None = None,
    ) -> list[dict[str, Any]]:
        """بحث دلالي باستخدام مسافة الكوساين (<=>) مع فلترة اختيارية.

        يعيد النتائج مرتبة حسب التشابه descending مع حساب score طبيعية.
        """
        conditions: list[str] = []
        params: dict[str, Any] = {"lim": limit}
        if subject is not None:
            conditions.append("subject = :subject")
            params["subject"] = subject
        if grade is not None:
            conditions.append("grade = :grade")
            params["grade"] = grade

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        emb_str = "[" + ",".join(f"{x:.8f}" for x in query_embedding) + "]"

        stmt = text(
            f"""
            SELECT id, content, subject, grade, chapter, source, metadata_, created_at,
                   (embedding <=> CAST(:emb AS vector)) AS distance
            FROM knowledge_chunks
            {where_sql}
            ORDER BY distance
            LIMIT :lim
            """
        )

        result = await self._session.execute(stmt, {"emb": emb_str, **params})
        rows = result.mappings().all()

        return [
            {
                **dict(row),
                "score": round(1.0 / (1.0 + max(0.0, float(row["distance"]))), 4),
            }
            for row in rows
        ]
