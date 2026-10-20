"""اختبارات تكامل لـ Indexer (المرحلة 3)."""

import asyncio
import tempfile
from pathlib import Path

from sqlalchemy import text

import pytest

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import open_session_factory
from retrieval.indexer import index_path
from retrieval.tools import CurriculumRetrievalTools

_DIM = 768


def _vec(values: list[float]) -> list[float]:
    return values + [0.0] * (_DIM - len(values))


async def _fake_embed(text: str) -> list[float]:
    _ = text
    return _vec([1.0, 0.0, 0.0])


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def test_indexer_basic() -> None:
    """فهرسة مجلد تجريبي (md + txt) → search يجد المحتوى."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                await session.execute(text("DELETE FROM knowledge_chunks"))
                await session.commit()
                repo = KnowledgeRepository(session)
                tools = CurriculumRetrievalTools(repo, _fake_embed)

                with tempfile.TemporaryDirectory() as tmpdir:
                    (Path(tmpdir) / "نحو.md").write_text(
                        "# الباب الأول\n\nالفاعل مرفوع Always.\n\n## الفاعل\n\nالفاعل مرفوع.\n",
                        encoding="utf-8",
                    )
                    (Path(tmpdir) / "صرف.txt").write_text(
                        "الصرف: الفعل الماضي مبني على الفتح.\n",
                        encoding="utf-8",
                    )

                    summary = await index_path(tmpdir, repo, _fake_embed)
                    await session.commit()

                    assert summary["files"] == 2
                    assert summary["chunks"] >= 2
                    assert summary["errors"] == []

                    sources = await tools.list_sources()
                    assert "نحو.md" in sources
                    assert "صرف.txt" in sources

                    results = await tools.search_curriculum(query="test", top_k=5)
                    assert len(results) >= 1

    asyncio.run(scenario())


def test_indexer_frontmatter() -> None:
    """فهرسة ملف مع frontmatter → metadata مستخرجة."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                repo = KnowledgeRepository(session)

                with tempfile.TemporaryDirectory() as tmpdir:
                    content = """---
subject: نحو
grade: أول إعدادي
chapter: الباب الأول
---
# الفاعل

الفاعل مرفوع.
"""
                    (Path(tmpdir) / "test.md").write_text(content, encoding="utf-8")

                    summary = await index_path(tmpdir, repo, _fake_embed)
                    await session.commit()

                    assert summary["files"] == 1
                    assert summary["chunks"] >= 1

                    from sqlalchemy import text

                    res = await session.execute(
                        text("SELECT subject, grade, chapter, source FROM knowledge_chunks WHERE source = 'test.md' LIMIT 1;")
                    )
                    row = res.fetchone()
                    assert row[0] == "نحو"
                    assert row[1] == "أول إعدادي"
                    assert row[2] == "الباب الأول"
                    assert row[3] == "test.md"

    asyncio.run(scenario())


def test_indexer_empty_dir() -> None:
    """فهرسة مجلد فارغ → 0 ملفات، 0 قطع."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                repo = KnowledgeRepository(session)

                with tempfile.TemporaryDirectory() as tmpdir:
                    summary = await index_path(tmpdir, repo, _fake_embed)
                    assert summary["files"] == 0
                    assert summary["chunks"] == 0
                    assert summary["errors"] == []

    asyncio.run(scenario())


def test_indexer_not_found() -> None:
    """مسار غير موجود → errors."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                repo = KnowledgeRepository(session)

                summary = await index_path("/nonexistent/path", repo, _fake_embed)
                assert summary["files"] == 0
                assert len(summary["errors"]) > 0

    asyncio.run(scenario())

