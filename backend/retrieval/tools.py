"""أدوات استرجاع المعرفة (المرحلة 2): طبقة رقيقة فوق KnowledgeRepository."""

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.knowledge import KnowledgeChunk
from db.repositories.knowledge_repository import KnowledgeRepository

EmbedQuery = Callable[[str], Awaitable[list[float]]]


class CurriculumRetrievalTools:
    """أدوات استرجاع المعرفة (المرحلة 2): بحث، جلب، قائمة مصادر.

    الاعتماديات (repository + embed_query) تُحقن من الخارج (DI).
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        embed_query: EmbedQuery,
    ) -> None:
        self._repo = repository
        self._embed_query = embed_query

    async def search_curriculum(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """بحث دلالي في المعرفة.

        يولد embedding للاستعلام ثم يبحث عبر KnowledgeRepository.
        """
        vector = await self._embed_query(query)
        results = await self._repo.search_similar(
            query_embedding=vector,
            limit=top_k,
            subject=subject,
            grade=grade,
        )
        return [self._format_result(row) for row in results]

    async def search_lesson_candidates(
        self,
        query: str,
        subject: str | None = None,
        *,
        per_grade: int = 2,
        global_k: int = 12,
    ) -> list[dict[str, Any]]:
        """جمع مرشحي درس من كل الصفوف، لا من الصف الحالي فقط.

        البحث العام يلتقط المقاطع بلا صف، والبحث لكل صف يضمن ألا يهيمن
        صف واحد على النتائج. البحث النصي يكمل عند ضعف التشابه الدلالي.
        """
        vector = await self._embed_query(query)
        rows: list[dict[str, Any]] = await self._repo.search_similar(
            query_embedding=vector,
            limit=global_k,
            subject=subject,
        )
        for grade in await self._repo.list_distinct_grades(subject):
            rows.extend(
                await self._repo.search_similar(
                    query_embedding=vector,
                    limit=per_grade,
                    subject=subject,
                    grade=grade,
                )
            )

        # البحث النصي ليس مجرد احتياط: عنوان الدرس الحرفي يحدد نطاقه
        # بدقة أفضل من التشابه الدلالي وحده.
        rows.extend(
            await self._repo.search_lexical(
                query, subject=subject, limit=global_k
            )
        )

        return self._dedupe_results(rows)

    async def search_lexical(
        self,
        query: str,
        subject: str | None = None,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """بحث نصي عن عنوان الدرس، موسوم ليُفضّل كنطاق دقيق."""
        rows = await self._repo.search_lexical(
            query, subject=subject, limit=limit
        )
        return [
            {**self._format_result(row), "match": "lexical"} for row in rows
        ]

    async def list_scope(
        self,
        *,
        source: str,
        chapter: str | None = None,
        grade: str | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        """جلب كل مقاطع مصدر/فصل محدد، لا المرشحين الأقرب فقط."""
        rows = await self._repo.list_by_scope(
            source=source,
            chapter=chapter,
            grade=grade,
            limit=limit,
        )
        return [self._format_result(row) for row in rows]

    @staticmethod
    def _format_result(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "content": row["content"],
            "score": row.get("score", 0.5),
            "subject": row.get("subject"),
            "grade": row.get("grade"),
            "chapter": row.get("chapter"),
            "source": row.get("source"),
            "source_type": "curriculum",
        }

    @staticmethod
    def _dedupe_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id: dict[int, dict[str, Any]] = {}
        for row in rows:
            existing = by_id.get(row["id"])
            if existing is None or row.get("score", 0) > existing.get("score", 0):
                by_id[row["id"]] = row
        return sorted(
            by_id.values(),
            key=lambda item: item.get("score", 0),
            reverse=True,
        )


    async def get_chunk_by_id(self, chunk_id: int) -> dict[str, Any] | None:
        """جلب قطعة معرفية بالمعرف (id)."""
        session: AsyncSession = self._repo._session  # noqa: SLF001
        result = await session.get(KnowledgeChunk, chunk_id)
        if result is None:
            return None
        return {
            "id": result.id,
            "content": result.content,
            "subject": result.subject,
            "grade": result.grade,
            "chapter": result.chapter,
            "source": result.source,
            "metadata_": result.metadata_,
            "created_at": result.created_at,
        }

    async def list_sources(self) -> list[str]:
        """قائمة المصادر المتوفرة في قاعدة المعرفة."""
        session: AsyncSession = self._repo._session  # noqa: SLF001
        stmt = select(KnowledgeChunk.source).distinct()
        result = await session.execute(stmt)
        return [row[0] for row in result.all() if row[0] is not None]
