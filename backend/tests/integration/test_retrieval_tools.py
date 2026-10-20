"""اختبارات تكامل لأدوات الاسترجاع (المرحلة 2)."""

import asyncio
import selectors
from typing import Any

from sqlalchemy import text

import pytest

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import open_session_factory
from retrieval.tools import CurriculumRetrievalTools

# ويندوز يتطلب SelectorEventLoop للاتصال غير المتزامن ببوستجرس عبر psycopg.
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DIM = 768


def _vec(values: list[float]) -> list[float]:
    return values + [0.0] * (_DIM - len(values))


async def _fake_embed(text: str) -> list[float]:
    """embedding وهمي: يُرجع متجه ثابت (للاختبار)."""
    _ = text
    return _vec([1.0, 0.0, 0.0])


async def _run(scenario) -> None:
    database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
    async with open_session_factory(database_url) as factory:
        async with factory() as session:
            await session.execute(text("DELETE FROM knowledge_chunks"))
            await session.commit()
            repo = KnowledgeRepository(session)
            tools = CurriculumRetrievalTools(repo, _fake_embed)
            await scenario(tools, repo, session)
            await session.execute(text("DELETE FROM knowledge_chunks"))
            await session.commit()


def test_search_curriculum_returns_sorted_results() -> None:
    """search_curriculum يعيد نتائج مرتبة حسب التشابه."""

    async def scenario(tools, repo, session) -> None:
        await repo.add_chunk(
            content="نحو: الفاعل مرفوع",
            embedding=_vec([1.0, 0.0, 0.0]),
            subject="نحو",
            grade="أول إعدادي",
        )
        await repo.add_chunk(
            content="صرف: الفعل مبني",
            embedding=_vec([0.0, 0.0, 1.0]),
            subject="صرف",
            grade="أول إعدادي",
        )

        results = await tools.search_curriculum(
            query="query",
            subject="نحو",
            grade="أول إعدادي",
            top_k=5,
        )

        assert len(results) == 1
        assert results[0]["content"] == "نحو: الفاعل مرفوع"
        assert "score" in results[0]
        assert results[0]["subject"] == "نحو"

    asyncio.run(_run(scenario))


def test_get_chunk_by_id_found() -> None:
    """get_chunk_by_id يعيد قطعة موجودة."""

    async def scenario(tools, repo, session) -> None:
        chunk = await repo.add_chunk(
            content="قطعة للبحث",
            embedding=_vec([1.0, 0.0, 0.0]),
            subject="نحو",
        )
        await session.commit()

        found = await tools.get_chunk_by_id(chunk.id)
        assert found is not None
        assert found["content"] == "قطعة للبحث"
        assert found["subject"] == "نحو"

    asyncio.run(_run(scenario))


def test_get_chunk_by_id_not_found() -> None:
    """get_chunk_by_id يعيد None لقطعة غير موجودة."""

    async def scenario(tools, repo, session) -> None:
        result = await tools.get_chunk_by_id(999999)
        assert result is None

    asyncio.run(_run(scenario))


def test_list_sources() -> None:
    """list_sources يعيد مصادر مميزة."""

    async def scenario(tools, repo, session) -> None:
        await repo.add_chunk(
            content="قطعة 1",
            embedding=_vec([1.0, 0.0, 0.0]),
            source="كتاب A",
        )
        await repo.add_chunk(
            content="قطعة 2",
            embedding=_vec([0.0, 1.0, 0.0]),
            source="كتاب B",
        )
        await repo.add_chunk(
            content="قطعة 3",
            embedding=_vec([0.0, 0.0, 1.0]),
            source="كتاب A",
        )
        await session.commit()

        sources = await tools.list_sources()
        assert sorted(sources) == ["كتاب A", "كتاب B"]

    asyncio.run(_run(scenario))
