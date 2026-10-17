"""اختبارات تكامل لمستودع مقاطع المعرفة (KnowledgeRepository)."""

import asyncio
import selectors
from typing import Any

import pytest
from sqlalchemy import text

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import open_session_factory
from sqlalchemy import text

# ويندوز يتطلب SelectorEventLoop للاتصال غير المتزامن ببوستجرس عبر psycopg.
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _vec(values: list[float]) -> list[float]:
    """توسيع المتجه إلى 768 بعد بإضافة أصفار."""
    return values + [0.0] * (768 - len(values))


async def _run_test(test_fn) -> None:
    """تشغيل اختبار تكامل مع جلسة قاعدة بيانات."""
    database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
    async with open_session_factory(database_url) as factory:
        async with factory() as session:
            await session.execute(text("DELETE FROM knowledge_chunks"))
            await session.commit()
            repo = KnowledgeRepository(session)
            await test_fn(repo, session)
            await session.execute(text("DELETE FROM knowledge_chunks"))
            await session.commit()


def test_add_and_get_chunk() -> None:
    """إدراج قطعة واحدة والتحقق من الحقول المخزنة."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        chunk = await repo.add_chunk(
            content="قاعدة النحو: الفاعل مرفوع.",
            embedding=_vec([1.0, 0.0, 0.0]),
            subject="نحو",
            grade="أول إعدادي",
            chapter="الباب الأول",
            source="كتاب تجريبي",
            metadata_={"page": 10},
        )
        assert chunk.id is not None
        assert chunk.content == "قاعدة النحو: الفاعل مرفوع."
        assert chunk.subject == "نحو"
        assert chunk.grade == "أول إعدادي"
        assert chunk.metadata_ == {"page": 10}

    asyncio.run(_run_test(scenario))


def test_search_similar_returns_ordered_by_distance() -> None:
    """البحث الدلالي يعيد النتائج مرتبة حسب أقرب مسافة."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        await repo.add_chunk(
            content="نحو: الفاعل مرفوع",
            embedding=_vec([1.0, 0.0, 0.0]),
            subject="نحو",
            grade="أول إعدادي",
        )
        await repo.add_chunk(
            content="نحو: المفعول به منصوب",
            embedding=_vec([0.9, 0.1, 0.0]),
            subject="نحو",
            grade="أول إعدادي",
        )
        await repo.add_chunk(
            content="صرف: الفعل الماضي مبني",
            embedding=_vec([0.0, 0.0, 1.0]),
            subject="صرف",
            grade="أول إعدادي",
        )

        results = await repo.search_similar(
            query_embedding=_vec([1.0, 0.0, 0.0]),
            limit=5,
            subject="نحو",
            grade="أول إعدادي",
        )

        assert len(results) == 2
        assert results[0]["content"] == "نحو: الفاعل مرفوع"
        assert results[0]["score"] >= results[1]["score"]
        assert all(r["subject"] == "نحو" for r in results)

    asyncio.run(_run_test(scenario))


def test_search_similar_without_filters() -> None:
    """البحث بدون فلاتر يعيد جميع القطع المقبولة."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        await repo.add_chunk(
            content="قطعة أ",
            embedding=_vec([1.0, 0.0, 0.0]),
            subject="نحو",
        )
        await repo.add_chunk(
            content="قطعة ب",
            embedding=_vec([0.0, 1.0, 0.0]),
            subject="صرف",
        )

        results = await repo.search_similar(
            query_embedding=_vec([1.0, 0.0, 0.0]),
            limit=10,
        )

        assert len(results) == 2
        assert results[0]["content"] == "قطعة أ"
        assert 0.0 < results[0]["score"] <= 1.0

    asyncio.run(_run_test(scenario))


def test_add_chunks_batch() -> None:
    """الإرسال الدفعي يدرج عدة قطع بكفاءة."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        chunks = [
            {
                "content": "دفعة قطعة 1",
                "embedding": _vec([0.5, 0.5, 0.0]),
                "subject": "نحو",
                "grade": "ثاني إعدادي",
            },
            {
                "content": "دفعة قطعة 2",
                "embedding": _vec([0.4, 0.6, 0.0]),
                "subject": "نحو",
                "grade": "ثاني إعدادي",
            },
        ]
        await repo.add_chunks_batch(chunks)

        results = await repo.search_similar(
            query_embedding=_vec([0.5, 0.5, 0.0]),
            limit=5,
            subject="نحو",
            grade="ثاني إعدادي",
        )

        assert len(results) == 2
        assert all(r["grade"] == "ثاني إعدادي" for r in results)

    asyncio.run(_run_test(scenario))
