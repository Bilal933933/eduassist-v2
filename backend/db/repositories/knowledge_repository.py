"""مستودع مقاطع المعرفة: إدراج وبحث دلالي ونصي."""

from typing import Any

from sqlalchemy import select, text
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

    async def list_by_scope(
        self,
        *,
        source: str,
        chapter: str | None = None,
        grade: str | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        """جلب كل مقاطع مصدر/فصل واحد مرتبة بترتيب الفهرسة.

        هذا هو الفرق بين «أقرب المقاطع» و«كل معلومات الدرس»: بعد تحديد
        المصدر الصحيح نجلب بقية مقاطعه حتى لو لم تكن قريبة دلاليًا.
        """
        if not source.strip() or limit <= 0:
            return []

        conditions = ["source = :source"]
        params: dict[str, Any] = {"source": source, "lim": limit}
        if chapter is None:
            conditions.append("chapter IS NULL")
        else:
            conditions.append("chapter = :chapter")
            params["chapter"] = chapter
        if grade is not None:
            conditions.append("grade = :grade")
            params["grade"] = grade

        stmt = text(
            f"""
            SELECT id, content, subject, grade, chapter, source, metadata_, created_at
            FROM knowledge_chunks
            WHERE {' AND '.join(conditions)}
            ORDER BY id
            LIMIT :lim
            """
        )
        result = await self._session.execute(stmt, params)
        return [dict(row) for row in result.mappings().all()]

    async def search_lexical(
        self,
        term: str,
        *,
        subject: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """بحث نصي احتياطي في عنوان الدرس واسم المصدر ونص المقطع."""
        term = term.strip()
        if not term or limit <= 0:
            return []

        conditions = [
            "(content ILIKE :pattern OR chapter ILIKE :pattern "
            "OR source ILIKE :pattern)"
        ]
        params: dict[str, Any] = {"pattern": f"%{term}%", "lim": limit}
        if subject is not None:
            conditions.append("subject = :subject")
            params["subject"] = subject

        stmt = text(
            f"""
            SELECT id, content, subject, grade, chapter, source, metadata_, created_at
            FROM knowledge_chunks
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE
                    WHEN chapter ILIKE :pattern THEN 0
                    WHEN source ILIKE :pattern THEN 1
                    ELSE 2
                END,
                id
            LIMIT :lim
            """
        )
        result = await self._session.execute(stmt, params)
        return [dict(row) for row in result.mappings().all()]

    async def list_distinct_grades(
        self, subject: str | None = None
    ) -> list[str]:
        """قائمة الصفوف المفهرسة، لضمان تمثيل كل صف في جمع الدرس."""
        stmt = select(KnowledgeChunk.grade).where(
            KnowledgeChunk.grade.is_not(None)
        )
        if subject is not None:
            stmt = stmt.where(KnowledgeChunk.subject == subject)
        result = await self._session.execute(stmt.distinct())
        grades = {
            str(row[0]).strip()
            for row in result.all()
            if row[0] is not None and str(row[0]).strip()
        }
        return sorted(grades)
