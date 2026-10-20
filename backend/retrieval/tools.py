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
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "score": r["score"],
                "subject": r.get("subject"),
                "grade": r.get("grade"),
                "chapter": r.get("chapter"),
                "source": r.get("source"),
                "source_type": "curriculum",
            }
            for r in results
        ]

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
