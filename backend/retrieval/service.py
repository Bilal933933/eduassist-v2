"""خدمة استرجاع موحّدة (المرحلة 5): داخلي + خارجي + hybrid."""

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import SessionFactory
from retrieval.external import search_wikipedia, search_wikipedia_pages
from retrieval.lesson_knowledge import (
    MAX_CHUNKS_PER_GROUP,
    MAX_SOURCE_CHARS,
    MAX_WIKIPEDIA_PAGES,
    WIKIPEDIA_PAGES_WITH_INTERNAL,
    build_curriculum_sources,
    dedupe_sources,
    group_candidate_scopes,
    wikipedia_source,
)
from retrieval.tools import CurriculumRetrievalTools

logger = logging.getLogger("eduassist.retrieval.service")

EmbedFn = Callable[[str], Awaitable[list[float]]]

_ARABIC_MARKS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_STOP_WORDS = {
    "في",
    "من",
    "على",
    "عن",
    "إلى",
    "الى",
    "درس",
    "الدرس",
    "باب",
    "الباب",
    "كل",
    "جميع",
    "المصادر",
    "الصفوف",
}


def _normalize_arabic(value: str) -> str:
    value = _ARABIC_MARKS.sub("", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _topic_tokens(topic: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"\w+", _normalize_arabic(topic)):
        if raw in _STOP_WORDS or len(raw) <= 2:
            continue
        token = raw[2:] if raw.startswith("ال") and len(raw) > 3 else raw
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _filter_topic_pages(
    pages: list[dict[str, Any]],
    topic: str,
    subject: str | None = None,
) -> list[dict[str, Any]]:
    """يبقي صفحات ويكيبيديا التي يحمل عنوانها كلمات الدرس كلها."""
    tokens = _topic_tokens(topic)
    if subject:
        tokens.extend(
            token
            for token in _topic_tokens(subject)
            if token not in tokens
        )
    if not tokens:
        return pages
    matched: list[dict[str, Any]] = []
    for page in pages:
        title = _normalize_arabic(str(page.get("title") or ""))
        if title and all(
            re.search(
                rf"(?<!\w)(?:ال)?{re.escape(token)}(?!\w)",
                title,
            )
            for token in tokens
        ):
            matched.append(page)
    return matched or pages


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

    async def search_lesson_sources(
        self,
        topic: str,
        subject: str | None = None,
    ) -> list[dict[str, Any]]:
        """جمع كل مصادر درس واحد: المنهج بكل الصفوف ثم ويكيبيديا.

        فشل أحد المصدرين لا يسقط الآخر؛ والعقدة تتعامل مع القائمة الفارغة
        برسالة صريحة بدل توليد محتوى غير موثوق.
        """
        if not topic.strip():
            return []

        internal: list[dict[str, Any]] = []
        try:
            internal = await self._lesson_curriculum(topic, subject)
        except Exception as error:
            logger.warning("تعذر جمع مصادر الدرس الداخلية: %s", error)

        external_limit = (
            MAX_WIKIPEDIA_PAGES if not internal else WIKIPEDIA_PAGES_WITH_INTERNAL
        )
        subject_hint = subject.split("-")[-1].strip() if subject else ""
        external_query = topic
        if subject_hint and subject_hint not in topic:
            external_query = f"{topic} في {subject_hint}"
        try:
            pages = await search_wikipedia_pages(
                query=external_query,
                limit=external_limit,
                max_chars=MAX_SOURCE_CHARS,
            )
        except Exception as error:
            logger.warning("تعذّر جلب صفحات ويكيبيديا: %s", error)
            pages = []

        pages = _filter_topic_pages(pages, topic, subject_hint)
        external = [wikipedia_source(page) for page in pages]
        return dedupe_sources([*internal, *external])

    async def _lesson_curriculum(
        self,
        topic: str,
        subject: str | None,
    ) -> list[dict[str, Any]]:
        """جمع مقاطع الدرس من كل الصفوف ثم توسيع كل نطاق لجميع مقاطعه."""
        async with self._session_factory() as session:
            tools = CurriculumRetrievalTools(
                KnowledgeRepository(session), self._embed_fn
            )
            candidates = await tools.search_lesson_candidates(
                query=topic, subject=subject
            )
            if not candidates and subject:
                # اسم المادة قد يختلف بين الواجهة والفهرس؛ نعيد بلا فلتر
                # بدل إخفاء مصادر موجودة بسبب اختلاف التسمية.
                candidates = await tools.search_lesson_candidates(
                    query=topic, subject=None
                )

            # عنوان الدرس الحرفي أدق من التشابه وحده؛ إن وجد نطاقًا نصيًا
            # نعتمد عليه ونستبعد الدروس الأخرى التي قد تتشابه متجهاتها.
            anchors = await tools.search_lexical(topic, subject=subject)
            scopes = group_candidate_scopes(anchors)
            if not scopes:
                scopes = group_candidate_scopes(candidates)
            groups: list[dict[str, Any]] = []
            for scope in scopes:
                chunks = await tools.list_scope(
                    source=scope["source"],
                    chapter=scope["chapter"],
                    grade=scope["grade"],
                    limit=MAX_CHUNKS_PER_GROUP,
                )
                groups.append({**scope, "chunks": chunks})
        return build_curriculum_sources(groups)
