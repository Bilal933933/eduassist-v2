"""خدمة استرجاع موحّدة (المرحلة 5): داخلي + خارجي + hybrid."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import SessionFactory
from retrieval.external import search_wikipedia
from retrieval.tools import CurriculumRetrievalTools

logger = logging.getLogger("eduassist.retrieval.service")

EmbedFn = Callable[[str], Awaitable[list[float]]]


class RetrievalService:
    """واجهة موحّدة للاسترجاع: داخلي، خارجي، hybrid.

    الاعتماديات (مصنع الجلسات، دالة التضمين) تُحقن من الخارج (DI).
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        embed_fn: EmbedFn,
        score_threshold: float = 0.65,
    ) -> None:
        self._session_factory = session_factory
        self._embed_fn = embed_fn
        self._score_threshold = score_threshold

    async def search_internal(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """بحث داخلي في المنهج (pgvector)."""
        async with self._session_factory() as session:
            tools = CurriculumRetrievalTools(
                KnowledgeRepository(session), self._embed_fn
            )
            return await tools.search_curriculum(
                query=query, subject=subject, grade=grade, top_k=top_k
            )

    async def search_external(
        self,
        query: str,
        lang: str = "ar",
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """بحث خارجي في ويكيبيديا."""
        return await search_wikipedia(query=query, lang=lang, top_k=top_k)

    async def search_hybrid(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
        top_k: int = 5,
        lang: str = "ar",
        external_top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """بحث hybrid: داخلي أولًا → إذا ضعفت النتائج، يُكمَّل من الخارج.

        شروط تفعيل الخارجي (أي واحد يكفي):
        1. لا توجد نتائج داخلية.
        2. أفضل score < score_threshold.
        3. عدد النتائج < top_k.
        """
        internal = await self.search_internal(
            query=query, subject=subject, grade=grade, top_k=top_k
        )
        for result in internal:
            result.setdefault("source_type", "curriculum")

        need_external = (
            not internal
            or internal[0].get("score", 0) < self._score_threshold
            or len(internal) < top_k
        )
        if not need_external:
            return internal

        external = await self.search_external(
            query=query, lang=lang, top_k=external_top_k
        )

        # دمج النتائج: داخلية أولاً، ثم خارجية
        merged: list[dict[str, Any]] = [*internal]
        for result in external:
            result.setdefault("source_type", "wikipedia")
            merged.append(result)

        return merged
