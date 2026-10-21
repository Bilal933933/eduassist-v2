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


def test_list_by_scope_returns_all_lesson_chunks() -> None:
    """جلب نطاق الدرس يعيد كل مقاطعه مرتبة، لا الأقرب دلاليًا فقط."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        for index in range(3):
            await repo.add_chunk(
                content=f"جزء {index} من درس كان وأخواتها",
                embedding=_vec([0.0, 1.0, 0.0]),
                subject="نحو",
                grade="أول إعدادي",
                chapter="كان وأخواتها",
                source="كتاب النحو.md",
            )
        await repo.add_chunk(
            content="درس آخر",
            embedding=_vec([1.0, 0.0, 0.0]),
            subject="نحو",
            grade="أول إعدادي",
            chapter="درس آخر",
            source="كتاب النحو.md",
        )

        rows = await repo.list_by_scope(
            source="كتاب النحو.md",
            chapter="كان وأخواتها",
            grade="أول إعدادي",
        )

        assert [row["content"] for row in rows] == [
            "جزء 0 من درس كان وأخواتها",
            "جزء 1 من درس كان وأخواتها",
            "جزء 2 من درس كان وأخواتها",
        ]

    asyncio.run(_run_test(scenario))


def test_search_lexical_matches_chapter_and_filters_subject() -> None:
    """البحث النصي يلتقط عنوان الدرس ويحترم المادة."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        await repo.add_chunk(
            content="محتوى بعيد دلاليًا",
            embedding=_vec([0.0, 0.0, 1.0]),
            subject="نحو",
            chapter="كان وأخواتها",
            source="نحو.md",
        )
        await repo.add_chunk(
            content="محتوى مادة أخرى",
            embedding=_vec([0.0, 0.0, 1.0]),
            subject="صرف",
            chapter="كان وأخواتها",
            source="صرف.md",
        )

        rows = await repo.search_lexical("كان وأخواتها", subject="نحو")

        assert [row["source"] for row in rows] == ["نحو.md"]

    asyncio.run(_run_test(scenario))


def test_list_distinct_grades_respects_subject() -> None:
    """قائمة الصفوف تستبعد الفارغ وتفلتر بالمادة عند تحديدها."""

    async def scenario(repo: KnowledgeRepository, session) -> None:
        await repo.add_chunk(
            content="أ", embedding=_vec([1.0]), subject="نحو", grade="أول إعدادي"
        )
        await repo.add_chunk(
            content="ب", embedding=_vec([1.0]), subject="نحو", grade="ثاني إعدادي"
        )
        await repo.add_chunk(
            content="ج", embedding=_vec([1.0]), subject="نحو", grade="أول إعدادي"
        )
        await repo.add_chunk(
            content="د", embedding=_vec([1.0]), subject="صرف", grade="ثالث إعدادي"
        )
        await repo.add_chunk(
            content="ه", embedding=_vec([1.0]), subject="نحو"
        )

        grades = await repo.list_distinct_grades(subject="نحو")

        assert grades == ["أول إعدادي", "ثاني إعدادي"]

    asyncio.run(_run_test(scenario))
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
