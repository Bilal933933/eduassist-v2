"""خدمة استرجاع موحّدة (المرحلة 5): داخلي + خارجي + hybrid."""

import logging
from collections.abc import Callable
from typing import Any

from db.repositories.knowledge_repository import KnowledgeRepository
from retrieval.external import search_wikipedia
from retrieval.tools import CurriculumRetrievalTools

logger = logging.getLogger("eduassist.retrieval.service")


class RetrievalService:
    """واجهة موحّدة للاسترجاع: داخلي، خارجي، hybrid.

    الاعتماديات (repository, tools, embed_fn) تُحقن من الخارج (DI).
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        tools: CurriculumRetrievalTools,
        embed_fn: Callable[[str], list[float]],
        score_threshold: float = 0.65,
    ) -> None:
        self._repo = repository
        self._tools = tools
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
        return await self._tools.search_curriculum(
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

        # إضافة source_type للنتائج الداخلية
        for r in internal:
            r.setdefault("source_type", "curriculum")

        need_external = False
        if not internal:
            need_external = True
        elif internal[0].get("score", 0) < self._score_threshold:
            need_external = True
        elif len(internal) < top_k:
            need_external = True

        if not need_external:
            # إضافة source_type للنتائج الداخلية
            for r in internal:
                r.setdefault("source_type", "curriculum")
            return internal

        external = await self.search_external(
            query=query, lang=lang, top_k=external_top_k
        )

        # دمج النتائج: داخلية أولاً، ثم خارجية
        merged: list[dict[str, Any]] = []
        for r in internal:
            r.setdefault("source_type", "curriculum")
            merged.append(r)
        for r in external:
            r.setdefault("source_type", "wikipedia")
            merged.append(r)

        return merged
